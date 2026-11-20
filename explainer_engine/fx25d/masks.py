import numpy as np, cv2
def sky_mask(im, depth, invalid):
    """General sky mask: connected to the top border, smooth (low gradient), far (invalid depth or depth above the 70th percentile),
    in the upper 70 % of the picture; feathered with a distance ramp so a pixel next to a non-sky pixel gets weight 0 (no halo)."""
    H, W = depth.shape; g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    grad = cv2.GaussianBlur(np.abs(cv2.Laplacian(cv2.GaussianBlur(g, (0, 0), 1.5), cv2.CV_32F)), (0, 0), 3)
    far = invalid | (depth > np.percentile(depth, 70))
    cand = (far & (grad < 7)).astype(np.uint8); cand[int(0.7 * H):] = 0
    top = g[: int(0.12 * H)][cand[: int(0.12 * H)] > 0]
    if top.size > 50:
        ref = float(np.median(top)); cand[(g < 0.62 * ref)] = 0  # darker than the sky seen at the top (far trench ends, ground): not sky
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab = cv2.connectedComponents(cand)
    keep = np.zeros_like(cand)
    for k in range(1, n):
        comp = lab == k
        if comp[:3].any() and comp.sum() > 0.01 * H * W: keep[comp] = 1
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    dist = cv2.distanceTransform(keep, cv2.DIST_L2, 5)
    w = np.clip((dist - 6) / 28.0, 0, 1)  # 0 within 6 px of any non-sky pixel, full after 34 px
    return cv2.GaussianBlur(w, (0, 0), 4)
