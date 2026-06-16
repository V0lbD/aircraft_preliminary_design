# Aircraft preliminary design calculation trace

- Schema version: `1.0`
- Calculation success: `True`
- Trace records: `43`

## preliminary_sizing

### 1. Cx_for_max_K

Коэффициент сопротивления для найденного максимального аэродинамического качества.

**Formula:**

$$
C_x = C_{x0} + \frac{C_y^2}{\pi e \lambda}
$$

**Values:**

- `C_x0` = `0.04`
- `C_y` = `2`
- `e` = `0.68`
- `Lambda` = `12.19`

**Result:**

`Cx_for_max_K` = `0.04`

---

### 2. K_max

Максимальное аэродинамическое качество по текущему численному поиску.

**Formula:**

$$
K_{max} = \frac{C_y}{C_x}
$$

**Values:**

- `C_y` = `2`
- `C_x` = `0.04`

**Result:**

`K_max` = `50`

---

### 3. p0_by_V_s

Ограничение по скорости сваливания.

**Formula:**

$$
p_{0,V_s} = \frac{1}{2} \cdot \rho_{V_s} \cdot V_s^2 \cdot C_{y,max}
$$

**Values:**

- `pho_V_s` = `1.225`
- `V_s` = `20`
- `C_y_max` = `1.6`

**Result:**

`p0_by_V_s` = `392` `N/m²`

---

### 4. P0_by_theta

Ограничение по градиенту набора высоты.

**Formula:**

$$
P_{0,\theta} = \begin{cases}\theta + 2\sqrt{\frac{C_{x0}}{\pi \lambda e}}, & N = 1 \\ \frac{N}{N - 1}\left(\theta + 2\sqrt{\frac{C_{x0}}{\pi \lambda e}}\right), & N > 1\end{cases}
$$

**Values:**

- `N` = `2`
- `theta` = `0.06`
- `C_x0` = `0.04`
- `Lambda` = `12.19`
- `e` = `0.68`

**Result:**

`P0_by_theta` = `0.276768`

---

### 5. P0_by_n_max

Ограничение по максимальной эксплуатационной перегрузке. В trace указан результат в оптимальной точке.

**Formula:**

$$
P_{0,n_{max}}(p_0) = \frac{C_{x0} \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}{p_0} + p_0 \cdot \frac{n_{max}^2}{\pi \lambda e \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}
$$

**Values:**

- `p0_optimal` = `260.842843`
- `C_x0` = `0.04`
- `pho_V_cruise` = `1.06`
- `V_cruise` = `48`
- `n_max` = `2.5`
- `Lambda` = `12.19`
- `e` = `0.68`
- `points_count` = `100`

**Result:**

`P0_by_n_max` = `0.238528`

---

### 6. P0_by_L_TODA

Ограничение по взлётной дистанции. В trace указан результат в оптимальной точке.

**Formula:**

$$
P_{0,L_{TODA}}(p_0) = \frac{p_0}{L_{TODA}} \cdot \frac{1}{C_{y,max,TO}} \cdot \frac{1}{\sigma}
$$

**Values:**

- `p0_optimal` = `260.842843`
- `L_TODA` = `150`
- `C_y_max_TO` = `2.6`
- `sigma` = `1`
- `points_count` = `100`

**Result:**

`P0_by_L_TODA` = `0.668828`

---

### 7. P0_by_V_y

Ограничение по скороподъёмности. В trace указан результат в оптимальной точке.

**Formula:**

$$
P_{0,V_y}(p_0) = \frac{V_y}{\sqrt{p_0}\sqrt{\frac{2}{\rho_{V_y}}\frac{1}{C_y}}} + \frac{C_x}{C_y}
$$

**Values:**

- `p0_optimal` = `260.842843`
- `V_y` = `10`
- `pho_V_y` = `1.1`
- `C_x` = `0.04`
- `C_y` = `2`
- `points_count` = `100`

**Result:**

`P0_by_V_y` = `0.669396`

---

### 8. P0_by_V_cruise

Ограничение по крейсерскому полёту. В trace указан результат в оптимальной точке.

**Formula:**

$$
P_{0,V_{cr}}(p_0) = \frac{C_{x0} \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}{p_0} + p_0 \cdot \frac{1}{\pi \lambda e \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}
$$

**Values:**

- `p0_optimal` = `260.842843`
- `C_x0` = `0.04`
- `pho_V_cruise` = `1.06`
- `V_cruise` = `48`
- `Lambda` = `12.19`
- `e` = `0.68`
- `points_count` = `100`

**Result:**

`P0_by_V_cruise` = `0.195464`

---

### 9. optimal_point

Выбор расчётной точки по огибающей ограничений.

**Formula:**

$$
P_{0,envelope}(p_0) = \max\left(P_{0,\theta}, P_{0,n_{max}}, P_{0,L_{TODA}}, P_{0,V_y}, P_{0,V_{cr}}\right), \quad (p_{0,opt}, P_{0,opt}) = \arg\min P_{0,envelope}(p_0)
$$

**Values:**

- `p0_by_V_s` = `392`
- `P0_by_theta` = `0.276768`
- `P0_by_n_max_at_optimal` = `0.238528`
- `P0_by_L_TODA_at_optimal` = `0.668828`
- `P0_by_V_y_at_optimal` = `0.669396`
- `P0_by_V_cruise_at_optimal` = `0.195464`
- `active_constraints` = `[19]`

**Result:**

`optimal_point` = `{"p0_optimal": 260.84284284284286, "P0_optimal": 0.6693964228601099}`

---

## mass_estimation

### 1. fuel_mass_ratio_breguet

Относительная масса топлива по Бреге.

**Formula:**

$$
\bar{m}_{т}=1-\exp\left(-\frac{LC_{e}g}{K\eta_{в}\cdot735.5\cdot3.6}\right)
$$

**Values:**

- `L_km` = `400`
- `C_e` = `0.26`
- `g` = `9.80665`
- `K` = `12`
- `eta_v` = `0.8`
- `hp_to_watt` = `735.5`

**Result:**

`fuel_mass_ratio_breguet` = `0.039329`

---

### 2. chumak_initial_mass_ratio_sum

Первое приближение суммы относительных масс по Чумаку.

**Formula:**

$$
\bar{m}_{к}+\bar{m}_{с.у}+\bar{m}_{об.СН}=0.60 \; \text{или} \; 0.61
$$

**Values:**

- `is_maneuverable` = `False`

**Result:**

`chumak_initial_mass_ratio_sum` = `0.61`

---

### 3. ice_initial_m0

Расчёт взлётной массы из баланса относительных масс.

**Formula:**

$$
m_{0,1}=\frac{m_{цн}+m_{сл}}{1-(\bar{m}_{к}+\bar{m}_{с.у}+\bar{m}_{об.СН}+\bar{m}_{т})}
$$

**Values:**

- `payload_mass` = `520`
- `service_load_mass` = `1500`
- `chumak_total_ratio` = `0.61`
- `fuel_ratio` = `0.039329`
- `denominator` = `0.350671`
- `numerator` = `2020`

**Result:**

`ice_initial_m0` = `5760.386799` `kg`

---

### 4. special_equipment_mass_ratio

Относительная масса оборудования СН.

**Formula:**

$$
\bar{m}_{об.СН}=0.08 \; (n_{дв}=1), \quad \bar{m}_{об.СН}=0.11 \; (n_{дв}>1)
$$

**Values:**

- `engine_count` = `2`

**Result:**

`special_equipment_mass_ratio` = `0.11`

---

### 5. iteration_1.wing_mass_ratio

Относительная масса крыла как среднее двух формул.

**Formula:**

$$
m_{кр1}=0.002k_{м}m_0n_yf\left(0.6\left(\frac{\sqrt{S\lambda}}{2}\right)^2+1\right)+3S; m_{кр2}=0.0001k_{м}m_0n_yf\lambda(\eta+3)\sqrt{S/\eta}\sqrt{\varepsilon}; \bar{m}_{кр}=\frac{m_{кр1}+m_{кр2}}{2m_0}
$$

**Values:**

- `iteration` = `1`
- `m0` = `5760.386799`
- `S` = `25`
- `lambda` = `12.19`
- `eta` = `1.5`
- `epsilon` = `0.12`
- `k_m` = `0.8`
- `n_y` = `2.5`
- `f` = `2`
- `m_wing_1` = `2227.656547`
- `m_wing_2` = `178.748685`

**Result:**

`iteration_1.wing_mass_ratio` = `0.208875`

---

### 6. iteration_1.fuselage_mass_ratio

Относительная масса фюзеляжа.

**Formula:**

$$
G_{ф}=0.584k_{сх}G_0^{0.771}, \quad \bar{m}_{ф}=G_{ф}/m_0
$$

**Values:**

- `iteration` = `1`
- `m0` = `5760.386799`
- `wing_position` = `high`
- `k_sx` = `1`
- `G_f` = `463.149358`

**Result:**

`iteration_1.fuselage_mass_ratio` = `0.080402`

---

### 7. iteration_1.tail_mass_ratio

Относительная масса оперения по формуле Хоуви.

**Formula:**

$$
m_{г.о}=7.2S_{г.о}^{1.2}\left(0.4+\frac{3.6V_{кр}+113}{935}\right); m_{в.о}=6.8S_{в.о}^{1.2}\left(0.4+\frac{3.6V_{кр}+113}{1100}\right); \bar{m}_{оп}=\frac{m_{г.о}+m_{в.о}}{m_0}
$$

**Values:**

- `iteration` = `1`
- `m0` = `5760.386799`
- `V_cruise_m_s` = `48`
- `V_cruise_km_h` = `172.8`
- `S_go` = `6.25`
- `S_vo` = `3.75`
- `m_go` = `45.813051`
- `m_vo` = `21.916475`

**Result:**

`iteration_1.tail_mass_ratio` = `0.011758`

---

### 8. iteration_1.landing_gear_mass_ratio

Относительная масса шасси.

**Formula:**

$$
\bar{m}_{ш,base}=k_{кон}k_{обт}(11.3+6H_{ош})10^{-3}+0.005; \bar{m}_{ш}=\bar{m}_{ш,base}+\Delta\bar{m}_{тип}
$$

**Values:**

- `iteration` = `1`
- `landing_gear_material` = `medium_steel`
- `landing_gear_fairing` = `none`
- `landing_gear_type` = `wheeled`
- `has_brakes` = `True`
- `H_osh` = `0.6`
- `k_con` = `1`
- `k_obt` = `1`
- `base_ratio` = `0.0199`

**Result:**

`iteration_1.landing_gear_mass_ratio` = `0.0419`

---

### 9. iteration_1.structure_mass_ratio

Суммарная относительная масса конструкции.

**Formula:**

$$
\bar{m}_{к}=\bar{m}_{кр}+\bar{m}_{ф}+\bar{m}_{оп}+\bar{m}_{ш}
$$

**Values:**

- `iteration` = `1`
- `wing_ratio` = `0.208875`
- `fuselage_ratio` = `0.080402`
- `tail_ratio` = `0.011758`
- `landing_gear_ratio` = `0.0419`

**Result:**

`iteration_1.structure_mass_ratio` = `0.342936`

---

### 10. iteration_1.ice_powerplant_mass_ratio

Относительная масса ДВС-силовой установки по Бадягину и Мухамедову.

**Formula:**

$$
G_{с.у}=N_{дв}N_{e,взл}(\gamma_{дв}+k_N), \quad \bar{m}_{с.у}=G_{с.у}/m_0
$$

**Values:**

- `iteration` = `1`
- `m0` = `5760.386799`
- `engine_count` = `2`
- `engine_type` = `piston`
- `takeoff_power_hp` = `300`
- `gamma_engine` = `0.792154`
- `k_N` = `0.55`
- `powerplant_mass` = `805.292342`

**Result:**

`iteration_1.ice_powerplant_mass_ratio` = `0.139798`

---

### 11. iteration_1.updated_m0

Расчёт взлётной массы из баланса относительных масс.

**Formula:**

$$
m_{0,2}=\frac{m_{цн}+m_{сл}}{1-(\bar{m}_{к}+\bar{m}_{с.у}+\bar{m}_{об.СН}+\bar{m}_{т})}
$$

**Values:**

- `structure_mass_ratio` = `0.342936`
- `powerplant_mass_ratio` = `0.139798`
- `special_equipment_mass_ratio` = `0.11`
- `fuel_mass_ratio` = `0.039329`
- `denominator` = `0.367937`
- `iteration` = `1`
- `numerator` = `2020`

**Result:**

`iteration_1.updated_m0` = `5490.070537` `kg`

---

### 12. iteration_1.wing_loading_check

Проверка изменения нагрузки на крыло.

**Formula:**

$$
\Delta p_0=\left|\frac{p_{0,new}-p_{0,old}}{p_{0,old}}\right|
$$

**Values:**

- `iteration` = `1`
- `p0_old` = `230.415472`
- `p0_new` = `219.602821`
- `tolerance` = `0.1`

**Result:**

`iteration_1.wing_loading_check` = `0.046927`

---

### 13. T_TO

Взлётная тяга из блока предварительного расчёта.

**Formula:**

$$
T_{TO}=m_0gP_{0,opt}
$$

**Values:**

- `m0` = `5490.070537`
- `g` = `9.80665`
- `P0_optimal` = `0.669396`

**Result:**

`T_TO` = `36039.768047` `N`

---

### 14. S_W

Площадь крыла, сохранённая в старом выходном поле для блока геометрии.

**Formula:**

$$
S_W=S_{кр,final}
$$

**Values:**

- `final_wing_area` = `25`

**Result:**

`S_W` = `25` `m²`

---

## geometry

### 1. wing_span

Размах крыла.

**Formula:**

$$
l_{wing} = \sqrt{S_{wing} \cdot \lambda_{wing}}
$$

**Values:**

- `S_wing` = `25`
- `lambda_wing` = `12.19`

**Result:**

`wing_span` = `17.45709` `m`

---

### 2. wing_root_chord

Корневая хорда крыла.

**Formula:**

$$
b_{0,wing} = \frac{2S_{wing}}{l_{wing}\left(1 + \frac{1}{\eta_{wing}}\right)}
$$

**Values:**

- `S_wing` = `25`
- `l_wing` = `17.45709`
- `eta_wing` = `2.5`

**Result:**

`wing_root_chord` = `2.045833` `m`

---

### 3. wing_tip_chord

Концевая хорда крыла.

**Formula:**

$$
b_{k,wing} = \frac{b_{0,wing}}{\eta_{wing}}
$$

**Values:**

- `b0_wing` = `2.045833`
- `eta_wing` = `2.5`

**Result:**

`wing_tip_chord` = `0.818333` `m`

---

### 4. wing_le_sweep

Стреловидность крыла по передней кромке.

**Formula:**

$$
\chi_{LE} = \arctan\left(\tan(\chi_{1/4}) + \frac{b_0 - b_k}{2l}\right)
$$

**Values:**

- `sweep_wing_quarter` = `25`
- `b0_wing` = `2.045833`
- `bk_wing` = `0.818333`
- `l_wing` = `17.45709`

**Result:**

`wing_le_sweep` = `26.632175` `deg`

---

### 5. fuselage_length

Длина фюзеляжа.

**Formula:**

$$
L_f = k_f \cdot l_{wing}
$$

**Values:**

- `k_fuselage` = `1.2`
- `l_wing` = `17.45709`

**Result:**

`fuselage_length` = `20.948508` `m`

---

### 6. fuselage_diameter

Диаметр фюзеляжа.

**Formula:**

$$
d_f = \frac{L_f}{\lambda_f}
$$

**Values:**

- `L_fuselage` = `20.948508`
- `lambda_fuselage` = `9`

**Result:**

`fuselage_diameter` = `2.327612` `m`

---

### 7. fuselage_radius

Радиус фюзеляжа.

**Formula:**

$$
r_f = \frac{d_f}{2}
$$

**Values:**

- `d_fuselage` = `2.327612`

**Result:**

`fuselage_radius` = `1.163806` `m`

---

### 8. wing_vertical_position

Вертикальное положение крыла относительно фюзеляжа.

**Formula:**

$$
y_{wing} = \begin{cases}\frac{d_f}{2}, & \text{high wing} \\ 0, & \text{mid wing} \\ -\frac{d_f}{2}, & \text{low wing}\end{cases}
$$

**Values:**

- `wing_scheme` = `high`
- `d_fuselage` = `2.327612`

**Result:**

`wing_vertical_position` = `1.163806` `m`

---

### 9. horizontal_tail_area

Площадь горизонтального оперения.

**Formula:**

$$
S_{ht} = k_{ht} \cdot S_{wing}
$$

**Values:**

- `k_horizontal_tail` = `0.25`
- `S_wing` = `25`

**Result:**

`horizontal_tail_area` = `6.25` `m²`

---

### 10. horizontal_tail_span

Размах горизонтального оперения.

**Formula:**

$$
l_{ht} = \sqrt{S_{ht} \cdot \lambda_{ht}}
$$

**Values:**

- `S_ht` = `6.25`
- `lambda_horizontal_tail` = `4`

**Result:**

`horizontal_tail_span` = `5` `m`

---

### 11. horizontal_tail_root_chord

Корневая хорда горизонтального оперения.

**Formula:**

$$
b_{0,ht} = \frac{2S_{ht}}{l_{ht}\left(1 + \frac{1}{\eta_{ht}}\right)}
$$

**Values:**

- `S_ht` = `6.25`
- `l_ht` = `5`
- `eta_horizontal_tail` = `3`

**Result:**

`horizontal_tail_root_chord` = `1.875` `m`

---

### 12. horizontal_tail_tip_chord

Концевая хорда горизонтального оперения.

**Formula:**

$$
b_{k,ht} = \frac{b_{0,ht}}{\eta_{ht}}
$$

**Values:**

- `b0_ht` = `1.875`
- `eta_horizontal_tail` = `3`

**Result:**

`horizontal_tail_tip_chord` = `0.625` `m`

---

### 13. horizontal_tail_le_sweep

Стреловидность горизонтального оперения по передней кромке.

**Formula:**

$$
\chi_{LE,ht} = \arctan\left(\tan(\chi_{1/4,ht}) + \frac{b_{0,ht} - b_{k,ht}}{2l_{ht}}\right)
$$

**Values:**

- `sweep_horizontal_tail_quarter` = `30`
- `b0_ht` = `1.875`
- `bk_ht` = `0.625`
- `l_ht` = `5`

**Result:**

`horizontal_tail_le_sweep` = `35.082297` `deg`

---

### 14. horizontal_tail_x_position

Продольное положение горизонтального оперения.

**Formula:**

$$
x_{ht} = x_f + 0.75L_f
$$

**Values:**

- `x_fuselage` = `-7`
- `L_fuselage` = `20.948508`

**Result:**

`horizontal_tail_x_position` = `8.711381` `m`

---

### 15. vertical_tail_area

Площадь вертикального оперения.

**Formula:**

$$
S_{vt} = k_{vt} \cdot S_{wing}
$$

**Values:**

- `k_vertical_tail` = `0.15`
- `S_wing` = `25`

**Result:**

`vertical_tail_area` = `3.75` `m²`

---

### 16. vertical_tail_span

Размах/высота вертикального оперения.

**Formula:**

$$
l_{vt} = \sqrt{S_{vt} \cdot \lambda_{vt}}
$$

**Values:**

- `S_vt` = `3.75`
- `lambda_vertical_tail` = `1.5`

**Result:**

`vertical_tail_span` = `2.371708` `m`

---

### 17. vertical_tail_root_chord

Корневая хорда вертикального оперения.

**Formula:**

$$
b_{0,vt} = \frac{2S_{vt}}{l_{vt}\left(1 + \frac{1}{\eta_{vt}}\right)}
$$

**Values:**

- `S_vt` = `3.75`
- `l_vt` = `2.371708`
- `eta_vertical_tail` = `2`

**Result:**

`vertical_tail_root_chord` = `2.108185` `m`

---

### 18. vertical_tail_tip_chord

Концевая хорда вертикального оперения.

**Formula:**

$$
b_{k,vt} = \frac{b_{0,vt}}{\eta_{vt}}
$$

**Values:**

- `b0_vt` = `2.108185`
- `eta_vertical_tail` = `2`

**Result:**

`vertical_tail_tip_chord` = `1.054093` `m`

---

### 19. vertical_tail_le_sweep

Стреловидность вертикального оперения по передней кромке.

**Formula:**

$$
\chi_{LE,vt} = \arctan\left(\tan(\chi_{1/4,vt}) + \frac{b_{0,vt} - b_{k,vt}}{2l_{vt}}\right)
$$

**Values:**

- `sweep_vertical_tail_quarter` = `35`
- `b0_vt` = `2.108185`
- `bk_vt` = `1.054093`
- `l_vt` = `2.371708`

**Result:**

`vertical_tail_le_sweep` = `42.689363` `deg`

---

### 20. vertical_tail_x_position

Продольное положение вертикального оперения.

**Formula:**

$$
x_{vt} = x_f + 0.75L_f
$$

**Values:**

- `x_fuselage` = `-7`
- `L_fuselage` = `20.948508`

**Result:**

`vertical_tail_x_position` = `8.711381` `m`

---
