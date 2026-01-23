from __future__ import annotations
from fractions import Fraction
from math import ceil, isqrt

# -----------------------------
# Fast Chudnovsky partial sum (exact Fraction) via recurrence
# S = sum_{k>=0} M_k * L_k / X_k
# pi = (426880 * sqrt(10005)) / S
# -----------------------------

C3_OVER_24 = 262537412640768000  # 640320^3 / 24, used by standard recurrence
X_BASE = -262537412640768000     # -640320^3

def pi_interval_by_terms(K: int, sqrt_digits: int) -> tuple[Fraction, Fraction]:
    """
    Returns (pi_lo, pi_hi) as Fractions, guaranteed to contain pi.

    K: number of Chudnovsky terms included (k=0..K-1)
    sqrt_digits: decimal digits for bounding sqrt(10005) (via integer sqrt scaling)
    """

    # We'll compute the exact rational S_K = sum_{k=0..K-1} t_k using
    # a binary-splitting style pairwise recursion. Each term t_k is
    #    t_k = (-1)^k * (6k)!/(k!^3 (3k)!) * (13591409 + 545140134*k) / 640320^(3k)
    # We'll compute integer pairs (P,Q) such that S_K = P/Q exactly.

    from math import factorial, gcd

    if K <= 0:
        raise ValueError("K must be >= 1")

    def term_num_den(k: int) -> tuple[int, int]:
        """Return integers (num, den) for t_k = num/den exactly."""
        sign = -1 if (k & 1) else 1
        a = 13591409 + 545140134 * k
        num = sign * factorial(6 * k) * a
        den = factorial(3 * k) * (factorial(k) ** 3) * (640320 ** (3 * k))
        return num, den

    def pairwise_sum(a: int, b: int) -> tuple[int, int]:
        """Return (P,Q) for sum_{k=a..b-1} num_k/den_k as exact integers P/Q.
        This uses recursive pairwise combination and reduces by gcd at each step."""
        if a + 1 == b:
            return term_num_den(a)
        mid = (a + b) // 2
        p1, q1 = pairwise_sum(a, mid)
        p2, q2 = pairwise_sum(mid, b)
        # combine: p = p1/q1 + p2/q2 = (p1*q2 + p2*q1) / (q1*q2)
        p = p1 * q2 + p2 * q1
        q = q1 * q2
        g = gcd(p, q)
        if g > 1:
            p //= g
            q //= g
        return p, q

    P, Q = pairwise_sum(0, K)

    # compute next term t_K and t_{K+1} for tail bound (exact integers)
    numK, denK = term_num_den(K)
    numK1, denK1 = term_num_den(K + 1)
    # convert to absolute Fractions for ratio
    abs_tK = Fraction(abs(numK), denK)
    abs_tK1 = Fraction(abs(numK1), denK1)

    # apply alternating-series bound if applicable, else rho-based geometric bound
    if abs_tK == 0:
        R = Fraction(0, 1)
    else:
        signK = -1 if (K & 1) else 1
        signK1 = -1 if ((K + 1) & 1) else 1
        if signK != signK1 and abs_tK1 <= abs_tK:
            R = abs_tK
        else:
            rho = Fraction(abs_tK1 * 1, abs_tK)
            if rho >= 1:
                raise RuntimeError("rho>=1; need larger K to obtain a decreasing tail")
            R = abs_tK * rho / (1 - rho)

    S = Fraction(P, Q)

    S_lo = S - R
    S_hi = S + R

    # sqrt(10005) interval using integer sqrt scaling:
    # floor(sqrt(10005)*10^m) / 10^m <= sqrt(10005) < (floor+1)/10^m
    m = max(20, sqrt_digits)  # digits after decimal for the sqrt bound
    scale2 = 10 ** (2 * m)
    s = isqrt(10005 * scale2)
    sqrt_lo = Fraction(s, 10 ** m)
    sqrt_hi = Fraction(s + 1, 10 ** m)

    C_lo = Fraction(426880, 1) * sqrt_lo
    C_hi = Fraction(426880, 1) * sqrt_hi

    # pi = C / S, S>0
    pi_lo = C_lo / S_hi
    pi_hi = C_hi / S_lo
    return pi_lo, pi_hi


# -----------------------------
# Integer exact floor of (p/q)^(1/3) * 10^N
# Find largest y such that y^3 * q <= p * 10^(3N)
# -----------------------------

def icbrt_floor(n: int) -> int:
    """floor integer cube root of n (n>=0)"""
    if n < 0:
        raise ValueError("n must be >= 0")
    if n < 2:
        return n
    # good initial guess using bit length
    b = (n.bit_length() + 2) // 3
    x = 1 << b
    for _ in range(30):
        x2 = x * x
        if x2 == 0:
            break
        x = (2*x + n // x2) // 3
    while (x + 1) ** 3 <= n:
        x += 1
    while x ** 3 > n:
        x -= 1
    return x

def floor_scaled_cuberoot(p: int, q: int, N: int) -> int:
    T = 10 ** (3 * N)
    RHS = p * T
    hi = icbrt_floor(RHS // q + 1) + 3
    lo = 0
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if (mid * mid * mid) * q <= RHS:
            lo = mid
        else:
            hi = mid
    return lo


# -----------------------------
# Formatting (your exact spec)
# "0." alone on its own line
# then N digits, 4-digit groups separated by space
# newline every 8 digits (2 groups per line)
# -----------------------------

def format_grouped_truncated(y_scaled: int, N: int) -> str:
    if N == 0:
        return "0.\n"
    frac = str(y_scaled).rjust(N, "0")
    groups = [frac[i:i+4] for i in range(0, N, 4)]
    lines = []
    for i in range(0, len(groups), 2):
        lines.append((" ".join(groups[i:i+2])).rstrip())
    return "0.\n" + "\n".join(lines) + "\n"


def _groups_lines_from_digits(digits: str) -> list[str]:
    """Return list of formatted lines (no leading '0.') from digit string."""
    if not digits:
        return []
    groups = [digits[i:i+4] for i in range(0, len(digits), 4)]
    lines: list[str] = []
    for i in range(0, len(groups), 2):
        lines.append((" ".join(groups[i:i+2])).rstrip())
    return lines


def radius_digits_stream(N: int, block: int = 100) -> None:
    """Stream proven truncated digits of r to stdout.

    Prints `0.` on its own line, then prints digits in 4-digit groups
    separated by a space, with a newline every 8 digits (2 groups).
    Streams progressively: proves blocks of digits and prints newly
    proven lines as they become available.
    """
    if N < 0:
        raise ValueError("N must be >= 0")

    if N == 0:
        print("0.")
        return

    print("0.")
    produced = 0
    printed_lines: list[str] = []

    while produced < N:
        target = min(N, produced + block)
        # heuristic K start
        K = max(2, ceil((target + 10) / 14))
        sqrt_digits = N + 30
        while True:
            try:
                pi_lo, pi_hi = pi_interval_by_terms(K, sqrt_digits)
            except RuntimeError:
                K += 1
                continue

            x_lo = Fraction(3, 4) / pi_hi
            x_hi = Fraction(3, 4) / pi_lo

            y_lo = floor_scaled_cuberoot(x_lo.numerator, x_lo.denominator, target)
            y_hi = floor_scaled_cuberoot(x_hi.numerator, x_hi.denominator, target)

            if y_lo == y_hi:
                y = y_lo
                break
            K += 1

        digits = str(y).rjust(target, "0")
        lines = _groups_lines_from_digits(digits)
        # print only newly available lines
        for ln in lines[len(printed_lines):]:
            print(ln)
        printed_lines = lines
        produced = target



# -----------------------------
# Main: tighten pi interval until digits are fixed
# r = (3/(4*pi))^(1/3) is monotone decreasing in pi
# so:
#   r_lo = (3/(4*pi_hi))^(1/3)
#   r_hi = (3/(4*pi_lo))^(1/3)
# if floor(r_lo*10^N) == floor(r_hi*10^N), digits are proven correct
# -----------------------------

def radius_digits_truncated(N: int) -> str:
    if N < 0:
        raise ValueError("N must be >= 0")

    # heuristic start: ~14 digits per term
    K = max(2, ceil((N + 10) / 14))
    # sqrt(10005) bound digits: keep comfortably above N
    sqrt_digits = N + 30

    while True:
        try:
            pi_lo, pi_hi = pi_interval_by_terms(K, sqrt_digits)
        except RuntimeError:
            # tail bound could not be established (rho>=1); increase K
            K += 1
            continue

        x_lo = Fraction(3, 4) / pi_hi  # smaller (since pi_hi bigger)
        x_hi = Fraction(3, 4) / pi_lo  # larger

        y_lo = floor_scaled_cuberoot(x_lo.numerator, x_lo.denominator, N)
        y_hi = floor_scaled_cuberoot(x_hi.numerator, x_hi.denominator, N)

        if y_lo == y_hi:
            # proven correct
            return format_grouped_truncated(y_lo, N)

        # diagnostic: show progress and why not yet fixed
        print(f"Not fixed at K={K}: y_lo={y_lo} y_hi={y_hi}")
        K += 1


def read_N_loop() -> int:
    """
    Loop until user inputs an acceptable N.
    You can adjust MAX_N to protect runtime.
    """
    MAX_N = 20000  # adjust as you like
    while True:
        s = input("N (digits after decimal, 0..%d): " % MAX_N).strip()
        if not s:
            continue
        if s.lower() in {"q", "quit", "exit"}:
            raise SystemExit
        try:
            n = int(s)
        except ValueError:
            print("请输入整数，或输入 q 退出。")
            continue
        if n < 0:
            print("N 必须 >= 0。")
            continue
        if n > MAX_N:
            print(f"N 太大（>{MAX_N}），请换小一点，或你自行调高 MAX_N。")
            continue
        return n


if __name__ == "__main__":
    while True:
        N = read_N_loop()
        try:
            radius_digits_stream(N)
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            break