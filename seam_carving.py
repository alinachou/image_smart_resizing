"""
Image Smart Resizing Project
"""

import numpy as np
from skimage import color


def energy_function(image):
    """Computes energy of the input image.
    For each pixel, we will sum the absolute value of the gradient in each direction.
    Args:
        image: numpy array of shape (H, W, 3)
    Returns:
        out: numpy array of shape (H, W)
    """
    H, W, _ = image.shape
    out = np.zeros((H, W))
    gray_image = color.rgb2gray(image)

    axis_zero = np.absolute(np.gradient(gray_image, axis=0))
    axis_one = np.absolute(np.gradient(gray_image, axis=1))
    out = axis_zero + axis_one

    return out


def compute_cost(image, energy, axis=1):
    """Computes optimal cost map (vertical) and paths of the seams.
    Starting from the first row, compute the cost of each pixel as the sum of energy along the
    lowest energy path from the top.
    We also return the paths, which will contain at each pixel either -1, 0 or 1 depending on
    where to go up if we follow a seam at this pixel.
    In the case that energies are equal, choose the left-most path. 
    Use a stacked matrix with left, middle, and right costs
    to make cost and paths calculations easier.
    Args:
        image: not used for this function
               (this is to have a common interface with compute_forward_cost)
        energy: numpy array of shape (H, W)
        axis: compute cost in width (axis=1) or height (axis=0)
    Returns:
        cost: numpy array of shape (H, W)
        paths: numpy array of shape (H, W) containing values -1 (up and left), 0 (straight up), or 1 (up and right)
    """
    energy = energy.copy()

    if axis == 0:
        energy = np.transpose(energy, (1, 0))

    H, W = energy.shape

    cost = np.zeros((H, W))
    paths = np.zeros((H, W), dtype=np.int)

    # Initialization
    cost[0] = energy[0]
    paths[0] = 0  # we don't care about the first row of paths

    mat_of_one = np.ones((H, W))
    stack = np.zeros((3, W))
    cost_padded = np.pad(cost,((0,0),(1,1)),'constant', constant_values=(float('inf')))
    for i in range (1, H):  # loop through rows
        stack[0] = cost_padded[i-1, 0:W]
        stack[1] = cost_padded[i-1, 1:W+1]
        stack[2] = cost_padded[i-1, 2:W+2]
        cost_padded[i, 1:W+1] = np.amin(stack, axis=0) + energy[i]
        paths[i] = np.argmin(stack, axis=0) - mat_of_one[i]
    cost = cost_padded[:, 1:W+1]

    if axis == 0:
        cost = np.transpose(cost, (1, 0))
        paths = np.transpose(paths, (1, 0))

    # Check that paths only contains -1, 0 or 1
    assert np.all(np.any([paths == 1, paths == 0, paths == -1], axis=0)), \
           "paths contains other values than -1, 0 or 1"

    return cost, paths


def backtrack_seam(paths, end):
    """Backtracks the paths map to find the seam ending at (H-1, end)
    To do that, we start at the bottom of the image on position (H-1, end), and we
    go up row by row by following the direction indicated by paths:
        - left (value -1)
        - middle (value 0)
        - right (value 1)
    Args:
        paths: numpy array of shape (H, W) containing values -1, 0 or 1
        end: the seam ends at pixel (H, end)
    Returns:
        seam: np.array of indices of shape (H,). The path pixels are the (i, seam[i])
    """
    
    H, W = paths.shape
    # initialize with -1 to make sure that everything gets modified
    seam = - np.ones(H, dtype=np.int)

    # Initialization
    seam[H-1] = end

    for i in range(H-2, -1, -1):
        seam[i] = seam[i+1] + paths[i+1, seam[i+1]]

    # Check that seam only contains values in [0, W-1]
    assert np.all(np.all([seam >= 0, seam < W], axis=0)), "seam contains values out of bounds"

    return seam


def remove_seam(image, seam):
    """Remove a seam from the image.
    Args:
        image: numpy array of shape (H, W, C) or shape (H, W)
        seam: numpy array of shape (H,) containing indices of the seam to remove
    Returns:
        out: numpy array of shape (H, W-1, C) or shape (H, W-1)
             make sure that `out` has same type as `image`
    """

    # Add extra dimension if 2D input
    if len(image.shape) == 2:
        image = np.expand_dims(image, axis=2)

    out = None
    H, W, C = image.shape
    
    out = np.copy(image)
    M, N, C = out.shape
    for i in range(M):  # loop through rows
        out[i, seam[i]:N-1, :] = out[i, seam[i]+1:N, :]
    out = out[:,0:W-1,:]

    out = np.squeeze(out)  # remove last dimension if C == 1

    # Make sure that `out` has same type as `image`
    assert out.dtype == image.dtype, \
       "Type changed between image (%s) and out (%s) in remove_seam" % (image.dtype, out.dtype)

    return out


def reduce(image, size, axis=1, efunc=energy_function, cfunc=compute_cost, bfunc=backtrack_seam, rfunc=remove_seam):
    """Reduces the size of the image using the seam carving process.
    At each step, we remove the lowest energy seam from the image. We repeat the process
    until we obtain an output of desired size.
    SUPER IMPORTANT: IF YOU WANT TO PREVENT CASCADING ERRORS IN THE CODE OF reduce(), USE FUNCTIONS:
        - efunc (instead of energy_function)
        - cfunc (instead of compute_cost)
        - bfunc (instead of backtrack_seam)
        - rfunc (instead of remove_seam)
    Args:
        image: numpy array of shape (H, W, 3)
        size: size to reduce height or width to (depending on axis)
        axis: reduce in width (axis=1) or height (axis=0)
        efunc: energy function to use
        cfunc: cost function to use
        bfunc: backtrack seam function to use
        rfunc: remove seam function to use
    Returns:
        out: numpy array of shape (size, W, 3) if axis=0, or (H, size, 3) if axis=1
    """

    out = np.copy(image)
    if axis == 0:
        out = np.transpose(out, (1, 0, 2))

    H = out.shape[0]
    W = out.shape[1]

    assert W > size, "Size must be smaller than %d" % W

    assert size > 0, "Size must be greater than zero"

    # number of iterations
    num_it = W - size
    for i in range(num_it):
        energy = np.zeros((H, W))
        cost = np.zeros((H, W))
        paths = np.zeros((H, W), dtype=np.int)
        seam = - np.ones(H, dtype=np.int)
        
        energy = efunc(out)
        cost, paths = cfunc(out, energy)
        end = np.argmin(cost[H-1])
        seam = bfunc(paths, end)
        out = rfunc(out, seam)

    assert out.shape[1] == size, "Output doesn't have the right shape"

    if axis == 0:
        out = np.transpose(out, (1, 0, 2))

    return out


def duplicate_seam(image, seam):
    """Duplicates pixels of the seam, making the pixels on the seam path "twice larger".
    This function will be helpful in functions enlarge_naive and enlarge.
    Args:
        image: numpy array of shape (H, W, C)
        seam: numpy array of shape (H,) of indices
    Returns:
        out: numpy array of shape (H, W+1, C)
    """

    H, W, C = image.shape
    out = np.zeros((H, W + 1, C))

    out[:,0:W,:] = np.copy(image)
    M, N, C = out.shape
    for i in range(M):  # loop through rows
        out[i, seam[i]+1:N, :] = out[i, seam[i]:N-1, :]

    return out


def find_seams(image, k, axis=1, efunc=energy_function, cfunc=compute_cost, bfunc=backtrack_seam, rfunc=remove_seam):
    """Find the top k seams (with lowest energy) in the image.
    We act like if we remove k seams from the image iteratively, but we need to store their
    position to be able to duplicate them in function enlarge.
    We keep track of where the seams are in the original image with the array seams, which
    is the output of find_seams.
    We also keep an indices array to map current pixels to their original position in the image.
    SUPER IMPORTANT: IF YOU WANT TO PREVENT CASCADING ERRORS IN THE CODE OF find_seams(), USE FUNCTIONS:
        - efunc (instead of energy_function)
        - cfunc (instead of compute_cost)
        - bfunc (instead of backtrack_seam)
        - rfunc (instead of remove_seam)
    Args:
        image: numpy array of shape (H, W, C)
        k: number of seams to find
        axis: find seams in width (axis=1) or height (axis=0)
        efunc: energy function to use
        cfunc: cost function to use
        bfunc: backtrack seam function to use
        rfunc: remove seam function to use
    Returns:
        seams: numpy array of shape (H, W)
    """

    image = np.copy(image)
    if axis == 0:
        image = np.transpose(image, (1, 0, 2))

    H, W, C = image.shape
    assert W > k, "k must be smaller than %d" % W

    # Create a map to remember original pixel indices
    # At each step, indices[row, col] will be the original column of current pixel
    # The position in the original image of this pixel is: (row, indices[row, col])
    # We initialize `indices` with an array like (for shape (2, 4)):
    #     [[1, 2, 3, 4],
    #      [1, 2, 3, 4]]
    indices = np.tile(range(W), (H, 1))  # shape (H, W)

    # We keep track here of the seams removed in our process
    # At the end of the process, seam number i will be stored as the path of value i+1 in `seams`
    # An example output for `seams` for two seams in a (3, 4) image can be:
    #    [[0, 1, 0, 2],
    #     [1, 0, 2, 0],
    #     [1, 0, 0, 2]]
    seams = np.zeros((H, W), dtype=np.int)

    # Iteratively find k seams for removal
    for i in range(k):
        # Get the current optimal seam
        energy = efunc(image)
        cost, paths = cfunc(image, energy)
        end = np.argmin(cost[H - 1])
        seam = bfunc(paths, end)

        # Remove that seam from the image
        image = rfunc(image, seam)

        # Store the new seam with value i+1 in the image
        # We can assert here that we are only writing on zeros (not overwriting existing seams)
        assert np.all(seams[np.arange(H), indices[np.arange(H), seam]] == 0), \
            "we are overwriting seams"
        seams[np.arange(H), indices[np.arange(H), seam]] = i + 1

        # We remove the indices used by the seam, so that `indices` keep the same shape as `image`
        indices = rfunc(indices, seam)

    if axis == 0:
        seams = np.transpose(seams, (1, 0))

    return seams


def enlarge(image, size, axis=1, efunc=energy_function, cfunc=compute_cost, dfunc=duplicate_seam, bfunc=backtrack_seam, rfunc=remove_seam):
    """Enlarges the size of the image by duplicating the low energy seams.
    We start by getting the k seams to duplicate through function find_seams.
    We iterate through these seams and duplicate each one iteratively.
    SUPER IMPORTANT: IF YOU WANT TO PREVENT CASCADING ERRORS IN THE CODE OF enlarge(), USE FUNCTIONS:
        - efunc (instead of energy_function)
        - cfunc (instead of compute_cost)
        - dfunc (instead of duplicate_seam)
        - bfunc (instead of backtrack_seam)
        - rfunc (instead of remove_seam)
        - find_seams
    Args:
        image: numpy array of shape (H, W, C)
        size: size to reduce height or width to (depending on axis)
        axis: enlarge in width (axis=1) or height (axis=0)
        efunc: energy function to use
        cfunc: cost function to use
        dfunc: duplicate seam function to use
        bfunc: backtrack seam function to use
        rfunc: remove seam function to use
    Returns:
        out: numpy array of shape (size, W, C) if axis=0, or (H, size, C) if axis=1
    """

    out = np.copy(image)
    # Transpose for height resizing
    if axis == 0:
        out = np.transpose(out, (1, 0, 2))

    H, W, C = out.shape

    assert size > W, "size must be greather than %d" % W

    assert size <= 2 * W, "size must be smaller than %d" % (2 * W)

    num_it = size - W
    seams_matrix = find_seams(out, num_it, efunc=efunc, cfunc=cfunc, bfunc=bfunc, rfunc=rfunc)
    
    col_of_zeros = np.zeros((H))
    for i in range(num_it):
        row, col = np.where(seams_matrix == i+1)
        out = dfunc(out, col)
        seams_matrix = dfunc(seams_matrix[:,:,np.newaxis], col)
        seams_matrix = seams_matrix[:,:,0]

    if axis == 0:
        out = np.transpose(out, (1, 0, 2))

    return out


def compute_forward_cost(image, energy):
    """Computes forward cost map (vertical) and paths of the seams.
    Starting from the first row, compute the cost of each pixel as the sum of energy along the
    lowest energy path from the top.
    Make sure to add the forward cost introduced when we remove the pixel of the seam.
    We also return the paths, which will contain at each pixel either -1, 0 or 1 depending on
    where to go up if we follow a seam at this pixel.
    Args:
        image: numpy array of shape (H, W, 3) or (H, W)
        energy: numpy array of shape (H, W)
    Returns:
        cost: numpy array of shape (H, W)
        paths: numpy array of shape (H, W) containing values -1, 0 or 1
    """

    image = color.rgb2gray(image)
    H, W = image.shape

    cost = np.zeros((H, W))
    paths = np.zeros((H, W), dtype=np.int)

    # Initialization
    cost[0] = energy[0]
    for j in range(W):
        if j > 0 and j < W - 1:
            cost[0, j] += np.abs(image[0, j+1] - image[0, j-1])
    paths[0] = 0  # we don't care about the first row of paths

    cost_padded = cost
    mat_of_one = np.ones((H, W))
    stack = np.zeros((3, W))
    for i in range (1, H):  # loop through rows
        for j in range (W):  # loop through columns; left 
            if j > 0 and j < W-1:
                stack[0, j] = cost_padded[i-1, j-1] + np.absolute(image[i, j+1] - image[i, j-1]) + np.absolute(image[i-1, j] - image[i, j-1])
                stack[1, j] = cost_padded[i-1, j] + np.absolute(image[i, j+1] - image[i, j-1])
                stack[2, j] = cost_padded[i-1, j+1] + np.absolute(image[i, j+1] - image[i, j-1]) + np.absolute(image[i-1, j] - image[i, j+1])
            if j == 0:
                stack[0, j] = (float('inf'))
                stack[1, j] = cost_padded[i-1, j]
                stack[2, j] = cost_padded[i-1, j+1] + np.absolute(image[i-1, j] - image[i, j+1])
            if j == W-1:
                stack[0, j] = cost_padded[i-1, j-1] + np.absolute(image[i-1, j] - image[i, j-1])
                stack[1, j] = cost_padded[i-1, j]
                stack[2, j] =  (float('inf'))
                               
        min_index_arr = np.argmin(stack, axis=0)
        paths[i] = min_index_arr - mat_of_one[i]
        cost[i] = np.amin(stack, axis=0) + energy[i]

    # Check that paths only contains -1, 0 or 1
    assert np.all(np.any([paths == 1, paths == 0, paths == -1], axis=0)), \
           "paths contains other values than -1, 0 or 1"

    return cost, paths

def remove_object(image, mask):
    """Remove the object present in the mask.
    Returns an output image with same shape as the input image, but without the object in the mask.
    Args:
        image: numpy array of shape (H, W, 3)
        mask: numpy boolean array of shape (H, W)
    Returns:
        out: numpy array of shape (H, W, 3)
    """
    
    assert image.shape[:2] == mask.shape

    H, W, _ = image.shape
    out = np.copy(image)

    num_to_remove = np.array((H))
    n = []
    for i in range(H):
        num_to_remove = np.sum(mask[i],axis=0)
        n.append(num_to_remove)
    remove_size = np.amax(n)
    size_reduce = W - remove_size
    
    for i in range(remove_size+30):
        energy = energy_function(out)
        for i in range(energy.shape[0]):
            for j in range(energy.shape[1]):
                if(mask[i,j] == 1):
                    energy[i,j] = -100000
        cost, paths = compute_cost(out, energy)
        end = np.argmin(cost[H-1])
        seam = backtrack_seam(paths, end)
        out = remove_seam(out, seam)
    out = enlarge(out, W, 1, efunc=energy_function, cfunc=compute_cost, dfunc=duplicate_seam, bfunc=backtrack_seam, rfunc=remove_seam)

    assert out.shape == image.shape

    return out
