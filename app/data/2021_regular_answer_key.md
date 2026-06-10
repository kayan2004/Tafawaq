# Answer Key — Lebanese Baccalaureate Mathematics
## 2021 Regular Session

---

## Exercise I — (2 points)

| № | Answer | Justification | Mark |
|---|---|---|---|
| 1 | **c** | $f(x) = \ln(x^2 - 3x)$ requires $x^2 - 3x > 0$, i.e. $x(x-3) > 0$, so $x \in ]-\infty\,;\,0[\,\cup\,]3\,;\,+\infty[$ | 0.5 |
| 2 | **c** | $\ln(e^x+2)-x = \ln(e^x+2)-\ln(e^x) = \ln\!\left(\dfrac{e^x+2}{e^x}\right) = \ln\!\left(\dfrac{e^{x+2}}{e^x}\right)$ | 0.5 |
| 3 | **a** | $I = \Big[\ln(3+e^x)\Big]_0^1 = \ln(3+e) - \ln 4 = \ln\!\left(\dfrac{e+3}{4}\right)$ | 1 |
| 4 | **a** | $f$ is continuous and strictly decreasing on $[2;4]$ from $3<4$ to $-1<4$: no root there. $f$ is continuous and strictly increasing on $[4;5]$ from $-1<4$ to $6>4$: exactly one root there. | 1 |

---

## Exercise II — (3 points)

**1)** For $z = 0$:
$$z' = \frac{4i}{2+2i} = \frac{4i}{2(1+i)} = \frac{2i}{1+i} \cdot \frac{1-i}{1-i} = \frac{2i(1-i)}{2} = i(1-i) = i+1 = \sqrt{2}\,e^{i\pi/4}$$

**Mark: 1**

**2)** Algebraic form:
$$\frac{z_A - z_B}{z_C - z_B} = \frac{-2+2i+2i}{4+2i} = \frac{-2+4i}{4+2i} \cdot \frac{4-2i}{4-2i} = \frac{(-2+4i)(4-2i)}{20} = \frac{-8+4i+16i-8i^2}{20} = \frac{0+20i}{20} = i$$

Since $\left|\dfrac{z_A-z_B}{z_C-z_B}\right| = 1$ and $\arg\!\left(\dfrac{z_A-z_B}{z_C-z_B}\right) = \dfrac{\pi}{2}\ [2\pi]$, triangle $ABC$ is **right isosceles at $B$**.

**Mark: 1**

**3a)** Verification:
$$z' = \frac{2z+4i}{iz+2+2i} = \frac{2(z+2i)}{i(z+2-2i)} = \frac{2(z-(-2i))}{i(z-(-2+2i))} = \frac{2(z-z_B)}{i(z-z_A)}$$

**Mark: 0.5**

**3b)** Modulus:
$$|z'| = \frac{|2|\,|z-z_B|}{|i|\,|z-z_A|} = \frac{2\,BM}{AM} \implies |OM'| = \frac{2\,BM}{AM}$$

**Mark: 1**

**3c)** When $M$ is on the perpendicular bisector of $[AB]$, $AM = BM$, so:
$$|OM'| = \frac{2\,BM}{AM} = 2$$

Therefore $M'$ moves on the **circle with center $O$ and radius $2$**.

**Mark: 1**

---

## Exercise III — (3 points)

### Part A

**A1)** The number of possible outcomes is $C_{10}^2 = \dfrac{10 \times 9}{2} = 45$. **Mark: 1**

**A2)**
$$P(A) = \frac{C_6^2 + C_4^2}{C_{10}^2} = \frac{15+6}{45} = \frac{21}{45} = \frac{7}{15}$$
$$P(B) = 1 - P(A) = \frac{8}{15} \quad \text{or} \quad P(B) = \frac{C_6^1 \cdot C_4^1}{C_{10}^2} = \frac{24}{45} = \frac{8}{15}$$

**Mark: 1**

### Part B

**B1)**
$$P(F \mid E) = P(A) = \frac{7}{15}$$
$$P(F \cap E) = P(F \mid E) \times P(E) = \frac{7}{15} \times \frac{1}{2} = \frac{7}{30} \checkmark$$

**Mark: 1**

**B2)** With replacement (odd die), color is chosen independently:
$$P(F \mid \bar{E}) = \frac{6 \times 6 + 4 \times 4}{10 \times 10} = \frac{36+16}{100} = \frac{52}{100} = \frac{13}{25}$$
$$P(F \cap \bar{E}) = \frac{13}{25} \times \frac{1}{2} = \frac{13}{50} \checkmark$$
$$P(F) = P(F \cap E) + P(F \cap \bar{E}) = \frac{7}{30} + \frac{13}{50} = \frac{35}{150} + \frac{39}{150} = \frac{74}{150} = \frac{37}{75}$$

**Mark: 1**

**B3)** By Bayes' theorem:
$$P(E \mid F) = \frac{P(F \cap E)}{P(F)} = \frac{\dfrac{7}{30}}{\dfrac{37}{75}} = \frac{7}{30} \times \frac{75}{37} = \frac{525}{1110} = \frac{35}{74}$$

**Mark: 0.5**

---

## Exercise IV — (4 points)

**1)** $S: B \to D$, $A \to E$, so:
$$k = \frac{DE}{AB} = \frac{2}{1} = 2$$

$(\overrightarrow{BC}\,;\,\overrightarrow{DG}) = \pi\ [2\pi]$, $DG = 2$, and $S(B) = D$, so $S(C) = G$. **Mark: 1**

**2)** The center of $S$ lies on both $(T)$ and $(T')$ because the rotation angle is $\dfrac{\pi}{2}$ and $S(B) = D$, $S(A) = E$. So the center is $W$ or $A$. Since $S(A) = E \neq A$, point $A$ is not invariant, therefore **$W$ is the center of $S$**. **Mark: 1**

**3a)** $S$ maps $(BD)$ to the line through $D = S(B)$ perpendicular to $(BD)$, which is $(DF)$. **Mark: 0.5**

**3b)** $S$ maps $(AD)$ to the line through $E = S(A)$ perpendicular to $(AD)$, which is $(EF)$. **Mark: 0.5**

**3c)** $\{D\} = (BD) \cap (AD)$, so:
$$\{S(D)\} = S(BD) \cap S(AD) = (DF) \cap (EF) = \{F\} \implies S(D) = F$$

**Mark: 0.5**

**4a)** $h = S \circ S$ is a similitude of center $W$, ratio $k^2 = 4$, angle $\pi$, which is a **homothety $\mathcal{H}(W,\,-4)$**. **Mark: 0.5**

**4b)**
$$h(B) = S(S(B)) = S(D) = F$$
Since $h = \mathcal{H}(W,-4)$: $\overrightarrow{WF} = -4\,\overrightarrow{WB}$ **Mark: 1**

**5a)** Setting up coordinates with $C(0,0)$, $D(1,0)$, $B(0,1)$, $F(3,2)$:

$h: z' = az + b$ with $a = -4$ (ratio $-4$).  
$h(B) = F \Rightarrow 3+2i = -4(i) + b \Rightarrow b = 3+6i$

$$\boxed{h: z' = -4z + 3 + 6i}$$

**Mark: 0.5**

**5b)** $W$ is the fixed point of $h$:
$$z_W = -4z_W + 3+6i \implies 5z_W = 3+6i \implies z_W = \frac{3}{5} + \frac{6}{5}i$$

$$W\!\left(\frac{3}{5}\,;\,\frac{6}{5}\right)$$

**Mark: 0.5**

---

## Exercise V — (8 points)

### Part A

**A1)**
$$\lim_{x \to -\infty} g(x) = \lim_{x \to -\infty}\bigl[(x+1)e^x - 1\bigr] = 0 + 0 - 1 = -1 \quad \text{(since } \lim_{x\to-\infty} xe^x = 0\text{)}$$
$$\lim_{x \to +\infty} g(x) = +\infty$$

**Mark: 1**

**A2)** $g'(x) = e^x + (x+1)e^x = (x+2)e^x$

$g'(x) = 0 \Leftrightarrow x = -2$; $g'(x) < 0$ for $x < -2$; $g'(x) > 0$ for $x > -2$.

$g(-2) = (-1)e^{-2} - 1 = -e^{-2} - 1$

| $x$ | $-\infty$ | | $-2$ | | $+\infty$ |
|---|---|---|---|---|---|
| $g'(x)$ | | $-$ | $0$ | $+$ | |
| $g(x)$ | $-1$ | $\searrow$ | $-e^{-2}-1$ | $\nearrow$ | $+\infty$ |

**Mark: 1**

**A3)** $g(0) = (0+1)e^0 - 1 = 1 - 1 = 0$.

On $]-\infty\,;\,0[$: the maximum of $g$ is $g(0) = 0$ approached but not reached (minimum is $-e^{-2}-1 < 0$); since $g$ is increasing on $[-2;0]$ from $-e^{-2}-1$ to $0$ and decreasing before $-2$, and $g$ is always strictly below $0$ on $]-\infty;0[$. Formally: $g(0)=0$ and $g$ is strictly increasing on $[-2;+\infty[$, so for $x < 0$: $g(x) < g(0) = 0$.  

On $]0;+\infty[$: $g(0) = 0$ is the minimum on $[-2;+\infty[$, so $g(x) > 0$ for $x > 0$.

**Mark: 1.5**

### Part B

**B1a)**
$$\lim_{x \to -\infty} f(x) = \lim_{x \to -\infty} x(e^x - 1) = (-\infty)(0-1) = +\infty$$
$$\lim_{x \to -\infty} [f(x) - (-x)] = \lim_{x \to -\infty} [f(x)+x] = \lim_{x \to -\infty} xe^x = 0$$

Therefore $(d): y = -x$ is an oblique asymptote to $(C)$ at $-\infty$. **Mark: 1**

**B1b)** $f(x) + x = xe^x$.

- If $x \in ]-\infty\,;\,0[$: $xe^x < 0$, so $(C)$ is **below** $(d)$.
- If $x = 0$: $xe^x = 0$, so $(C)$ and $(d)$ **intersect** at $O$.
- If $x \in ]0\,;\,+\infty[$: $xe^x > 0$, so $(C)$ is **above** $(d)$.

**Mark: 1**

**B2)**
$$\lim_{x \to +\infty} f(x) = \lim_{x \to +\infty} x(e^x-1) = +\infty$$
$$f(2) = 2(e^2-1) \approx 12.78$$

**Mark: 1**

**B3)** $f'(x) = e^x - 1 + xe^x = (x+1)e^x - 1 = g(x)$.

From Part A: $f'(x) = g(x) < 0$ for $x < 0$, $f'(0) = 0$, $f'(x) > 0$ for $x > 0$.

| $x$ | $-\infty$ | | $0$ | | $+\infty$ |
|---|---|---|---|---|---|
| $f'(x)$ | | $-$ | $0$ | $+$ | |
| $f(x)$ | $+\infty$ | $\searrow$ | $0$ | $\nearrow$ | $+\infty$ |

**Mark: 1.5**

**B4)** $f''(x) = g'(x) = (x+2)e^x$. 

$f''(-2) = 0$ and $f''$ changes sign at $x = -2$ (negative before, positive after), so $(C)$ has a **point of inflection** at $I(-2\,;\,f(-2))$.

$f(-2) = -2(e^{-2}-1) = 2 - 2e^{-2}$, so $I = (-2\,;\,2-2e^{-2})$. **Mark: 0.5**

**B5)** *(Graph — draw $(d)$: line through $O$ with slope $-1$; draw $(C)$ with minimum at $(0,0)$, asymptote $(d)$ at $-\infty$, point of inflection at $I(-2\,;\,2-2e^{-2})$.)* **Mark: 1**

**B6a)** $\dfrac{d}{dx}\bigl[(x-1)e^x\bigr] = e^x + (x-1)e^x = xe^x$.

Therefore $\displaystyle\int xe^x\,dx = (x-1)e^x + k$, $k \in \mathbb{R}$. **Mark: 1**

**B6b)** On $[\alpha\,;\,0]$, $(C)$ is below $(d)$ so:
$$A(\alpha) = \int_\alpha^0 \bigl(-x - f(x)\bigr)\,dx = \int_\alpha^0 (-x - xe^x + x)\,dx = \int_\alpha^0 -xe^x\,dx = \Big[(1-x)e^x\Big]_\alpha^0$$
$$= (1-0)e^0 - (1-\alpha)e^\alpha = 1 - (1-\alpha)e^\alpha$$

Since $f(\alpha) = 1$: $\alpha(e^\alpha - 1) = 1 \Rightarrow e^\alpha = 1 + \dfrac{1}{\alpha}$.

$$A(\alpha) = 1 - (1-\alpha)\!\left(1 + \frac{1}{\alpha}\right) = 1 - \left(1 + \frac{1}{\alpha} - \alpha - 1\right) = 1 - \frac{1}{\alpha} + \alpha = 1 + \alpha - \frac{1}{\alpha}$$

$$\boxed{A(\alpha) = 1 + \alpha - \frac{1}{\alpha} \text{ units of area}}$$

**Mark: 1.5**
