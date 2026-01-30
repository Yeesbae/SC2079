import math
from enum import Enum

class TurnType(Enum):
    LSL = 0
    RSR = 1
    LSR = 2
    RSL = 3
    RLR = 4
    LRL = 5

def mod2pi(theta):
    return theta - 2.0 * math.pi * math.floor(theta / (2.0 * math.pi))

def polar(x, y):
    r = math.hypot(x, y)
    theta = math.atan2(y, x)
    return r, theta

def dubins_shortest_path(q0, q1, rho):
    """
    q0, q1: (x, y, theta) where theta in radians
    rho: turning radius
    Returns: (total_length, (path_type, t, p, q))
    """
    dx = q1[0] - q0[0]
    dy = q1[1] - q0[1]
    D, theta = polar(dx, dy)
    d = D / rho

    if d < 1e-6:
        return 0.0, None

    alpha = mod2pi(q0[2] - theta)
    beta = mod2pi(q1[2] - theta)

    best_cost = float("inf")
    best_path = None

    for path_type in TurnType:
        result = dubins_word(path_type, alpha, beta, d)
        if result is None:
            continue

        t, p, q = result
        cost = (t + p + q) * rho
        if cost < best_cost:
            best_cost = cost
            best_path = (path_type, t, p, q)

    return best_cost, best_path

def dubins_word(path_type, alpha, beta, d):
    sa, sb = math.sin(alpha), math.sin(beta)
    ca, cb = math.cos(alpha), math.cos(beta)
    c_ab = math.cos(alpha - beta)

    if path_type == TurnType.LSL:
        tmp = 2 + d * d - 2 * c_ab + 2 * d * (sa - sb)
        if tmp < 0:
            return None
        p = math.sqrt(tmp)
        t = mod2pi(-alpha + math.atan2(cb - ca, d + sa - sb))
        q = mod2pi(beta - math.atan2(cb - ca, d + sa - sb))
        return t, p, q

    if path_type == TurnType.RSR:
        tmp = 2 + d * d - 2 * c_ab + 2 * d * (sb - sa)
        if tmp < 0:
            return None
        p = math.sqrt(tmp)
        t = mod2pi(alpha - math.atan2(ca - cb, d - sa + sb))
        q = mod2pi(-beta + math.atan2(ca - cb, d - sa + sb))
        return t, p, q

    if path_type == TurnType.LSR:
        tmp = -2 + d * d + 2 * c_ab + 2 * d * (sa + sb)
        if tmp < 0:
            return None
        p = math.sqrt(tmp)
        t = mod2pi(-alpha + math.atan2(-ca - cb, d + sa + sb))
        q = mod2pi(-beta + math.atan2(-ca - cb, d + sa + sb))
        return t, p, q

    if path_type == TurnType.RSL:
        tmp = -2 + d * d + 2 * c_ab - 2 * d * (sa + sb)
        if tmp < 0:
            return None
        p = math.sqrt(tmp)
        t = mod2pi(alpha - math.atan2(ca + cb, d - sa - sb))
        q = mod2pi(beta - math.atan2(ca + cb, d - sa - sb))
        return t, p, q

    if path_type == TurnType.RLR:
        tmp = (6 - d * d + 2 * c_ab + 2 * d * (sa - sb)) / 8
        if abs(tmp) > 1:
            return None
        p = mod2pi(2 * math.pi - math.acos(tmp))
        t = mod2pi(alpha - math.atan2(ca - cb, d - sa + sb) + p / 2)
        q = mod2pi(alpha - beta - t + p)
        return t, p, q

    if path_type == TurnType.LRL:
        tmp = (6 - d * d + 2 * c_ab + 2 * d * (sb - sa)) / 8
        if abs(tmp) > 1:
            return None
        p = mod2pi(2 * math.pi - math.acos(tmp))
        t = mod2pi(-alpha - math.atan2(ca - cb, d + sa - sb) + p / 2)
        q = mod2pi(beta - alpha - t + p)
        return t, p, q

    return None

def interpolate_dubins_path(dubins_path, rho, step_size=0.1):
    """
    Interpolate points along the Dubins path.

    Args:
        dubins_path: tuple (path_type, t, p, q)
        rho: turning radius
        step_size: distance step along path

    Returns:
        List of (x, y, theta) points
    """
    if dubins_path is None:
        return []

    path_type, t, p, q = dubins_path

    # Total path length
    total_length = (t + p + q) * rho
    num_points = max(2, int(total_length / step_size))

    points = []

    # Simple linear interpolation along path (rough approximation)
    for i in range(num_points + 1):
        s = i / num_points  # fraction along the path
        # Interpolate x, y, theta linearly (not exact Dubins, but usable for planning)
        theta = s * (t + p + q)
        points.append((s * t * rho, s * p * rho, theta))  # placeholder
        # TODO: replace with exact Dubins integration if high fidelity needed

    return points
