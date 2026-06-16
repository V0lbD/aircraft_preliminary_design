# Aircraft preliminary design calculation trace

- Schema version: `1.0`
- Calculation success: `True`
- Trace records: `68`

## preliminary_sizing

### 1. Cx_for_max_K

Коэффициент сопротивления для найденного максимального аэродинамического качества.

**Formula:**

$$
C_x = C_{x0} + \frac{C_y^2}{\pi e \lambda}
$$

**Values:**

- `C_x0` = `0.028`
- `C_y` = `2`
- `e` = `0.82`
- `Lambda` = `9.2`

**Result:**

`Cx_for_max_K` = `0.028`

---

### 2. K_max

Максимальное аэродинамическое качество по текущему численному поиску.

**Formula:**

$$
K_{max} = \frac{C_y}{C_x}
$$

**Values:**

- `C_y` = `2`
- `C_x` = `0.028`

**Result:**

`K_max` = `71.428571`

---

### 3. p0_by_V_s

Ограничение по скорости сваливания.

**Formula:**

$$
p_{0,V_s} = \frac{1}{2} \cdot \rho_{V_s} \cdot V_s^2 \cdot C_{y,max}
$$

**Values:**

- `pho_V_s` = `1.225`
- `V_s` = `52`
- `C_y_max` = `1.5`

**Result:**

`p0_by_V_s` = `2484.3` `N/m²`

---

### 4. P0_by_theta

Ограничение по градиенту набора высоты.

**Formula:**

$$
P_{0,\theta} = \begin{cases}\theta + 2\sqrt{\frac{C_{x0}}{\pi \lambda e}}, & N = 1 \\ \frac{N}{N - 1}\left(\theta + 2\sqrt{\frac{C_{x0}}{\pi \lambda e}}\right), & N > 1\end{cases}
$$

**Values:**

- `N` = `2`
- `theta` = `0.15`
- `C_x0` = `0.028`
- `Lambda` = `9.2`
- `e` = `0.82`

**Result:**

`P0_by_theta` = `0.437488`

---

### 5. P0_by_n_max

Ограничение по максимальной эксплуатационной перегрузке. В trace указан результат в оптимальной точке.

**Formula:**

$$
P_{0,n_{max}}(p_0) = \frac{C_{x0} \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}{p_0} + p_0 \cdot \frac{n_{max}^2}{\pi \lambda e \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}
$$

**Values:**

- `p0_optimal` = `705.974274`
- `C_x0` = `0.028`
- `pho_V_cruise` = `0.45`
- `V_cruise` = `185`
- `n_max` = `3.2`
- `Lambda` = `9.2`
- `e` = `0.82`
- `points_count` = `100`

**Result:**

`P0_by_n_max` = `0.345112`

---

### 6. P0_by_L_TODA

Ограничение по взлётной дистанции. В trace указан результат в оптимальной точке.

**Formula:**

$$
P_{0,L_{TODA}}(p_0) = \frac{p_0}{L_{TODA}} \cdot \frac{1}{C_{y,max,TO}} \cdot \frac{1}{\sigma}
$$

**Values:**

- `p0_optimal` = `705.974274`
- `L_TODA` = `850`
- `C_y_max_TO` = `1.9`
- `sigma` = `1`
- `points_count` = `100`

**Result:**

`P0_by_L_TODA` = `0.437136`

---

### 7. P0_by_V_y

Ограничение по скороподъёмности. В trace указан результат в оптимальной точке.

**Formula:**

$$
P_{0,V_y}(p_0) = \frac{V_y}{\sqrt{p_0}\sqrt{\frac{2}{\rho_{V_y}}\frac{1}{C_y}}} + \frac{C_x}{C_y}
$$

**Values:**

- `p0_optimal` = `705.974274`
- `V_y` = `10`
- `pho_V_y` = `1.1`
- `C_x` = `0.028`
- `C_y` = `2`
- `points_count` = `100`

**Result:**

`P0_by_V_y` = `0.408772`

---

### 8. P0_by_V_cruise

Ограничение по крейсерскому полёту. В trace указан результат в оптимальной точке.

**Formula:**

$$
P_{0,V_{cr}}(p_0) = \frac{C_{x0} \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}{p_0} + p_0 \cdot \frac{1}{\pi \lambda e \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}
$$

**Values:**

- `p0_optimal` = `705.974274`
- `C_x0` = `0.028`
- `pho_V_cruise` = `0.45`
- `V_cruise` = `185`
- `Lambda` = `9.2`
- `e` = `0.82`
- `points_count` = `100`

**Result:**

`P0_by_V_cruise` = `0.309369`

---

### 9. optimal_point

Выбор расчётной точки по огибающей ограничений.

**Formula:**

$$
P_{0,envelope}(p_0) = \max\left(P_{0,\theta}, P_{0,n_{max}}, P_{0,L_{TODA}}, P_{0,V_y}, P_{0,V_{cr}}\right), \quad (p_{0,opt}, P_{0,opt}) = \arg\min P_{0,envelope}(p_0)
$$

**Values:**

- `p0_by_V_s` = `2484.3`
- `P0_by_theta` = `0.437488`
- `P0_by_n_max_at_optimal` = `0.345112`
- `P0_by_L_TODA_at_optimal` = `0.437136`
- `P0_by_V_y_at_optimal` = `0.408772`
- `P0_by_V_cruise_at_optimal` = `0.309369`
- `active_constraints` = `[16]`

**Result:**

`optimal_point` = `{"p0_optimal": 705.9742742742743, "P0_optimal": 0.4374875049804911}`

---

## mass_estimation

### 1. m_OE_ratio

Относительная масса пустого самолёта по базовой оценочной формуле.

**Formula:**

$$
\bar{m}_{OE} = 0.23 + 1.04 \cdot P_{0,opt}
$$

**Values:**

- `P0_optimal` = `0.437488`

**Result:**

`m_OE_ratio` = `0.684987`

---

### 2. M_ff_non_cruise

Произведение массовых долей для некрейсерских участков миссии.

**Formula:**

$$
M_{ff,noncruise} = \prod_i M_{ff,i}
$$

**Values:**

- `engine_start` = `0.99`
- `taxi` = `0.995`
- `takeoff` = `0.995`
- `climb` = `0.98`
- `descent` = `0.99`
- `landing` = `0.992`

**Result:**

`M_ff_non_cruise` = `0.94331`

---

### 3. breguet_range_factor

Фактор дальности в формуле Бреге.

**Formula:**

$$
B = \frac{K \cdot V_{cruise}}{c \cdot g}
$$

**Values:**

- `cruise_L_D_ratio` = `13.5`
- `V_cruise` = `185`
- `cruise_sfc` = `1.800000e-05`
- `g` = `9.80665`

**Result:**

`breguet_range_factor` = `1.414856e+07` `m`

---

### 4. M_ff_cruise

Массовая доля для крейсерского участка по формуле Бреге.

**Formula:**

$$
M_{ff,cruise} = \exp\left(-\frac{L}{B}\right)
$$

**Values:**

- `design_range_m` = `2.000000e+06`
- `breguet_range_factor` = `1.414856e+07`

**Result:**

`M_ff_cruise` = `0.868179`

---

### 5. M_ff_total

Полная массовая доля миссии.

**Formula:**

$$
M_{ff,total} = M_{ff,noncruise} \cdot M_{ff,cruise}
$$

**Values:**

- `M_ff_non_cruise` = `0.94331`
- `M_ff_cruise` = `0.868179`

**Result:**

`M_ff_total` = `0.818962`

---

### 6. m_F_ratio

Относительная масса топлива.

**Formula:**

$$
\bar{m}_F = k_{reserve} \cdot \left(1 - M_{ff,total}\right)
$$

**Values:**

- `fuel_reserve_factor` = `1.15`
- `M_ff_total` = `0.818962`

**Result:**

`m_F_ratio` = `0.208194`

---

### 7. mass_balance_denominator

Знаменатель базового уравнения взлётной массы.

**Formula:**

$$
D = 1 - \bar{m}_F - \bar{m}_{OE}
$$

**Values:**

- `m_F_ratio` = `0.208194`
- `m_OE_ratio` = `0.684987`

**Result:**

`mass_balance_denominator` = `0.106819`

---

### 8. m_MTO_base

Базовая максимальная взлётная масса до компонентного уточнения.

**Formula:**

$$
m_{MTO} = \frac{m_{payload}}{1 - \bar{m}_F - \bar{m}_{OE}}
$$

**Values:**

- `payload_mass` = `1100`
- `m_F_ratio` = `0.208194`
- `m_OE_ratio` = `0.684987`
- `denominator` = `0.106819`

**Result:**

`m_MTO_base` = `10297.779318` `kg`

---

### 9. m_OE_base

Базовая масса пустого самолёта.

**Formula:**

$$
m_{OE} = m_{MTO} \cdot \bar{m}_{OE}
$$

**Values:**

- `m_MTO` = `10297.779318`
- `m_OE_ratio` = `0.684987`

**Result:**

`m_OE_base` = `7053.845015` `kg`

---

### 10. m_F_base

Базовая масса топлива.

**Formula:**

$$
m_F = m_{MTO} \cdot \bar{m}_F
$$

**Values:**

- `m_MTO` = `10297.779318`
- `m_F_ratio` = `0.208194`

**Result:**

`m_F_base` = `2143.934303` `kg`

---

### 11. useful_load_ratio

Относительная масса полезной нагрузки и топлива.

**Formula:**

$$
\bar{m}_{useful} = \frac{m_F + m_{payload}}{m_{MTO}}
$$

**Values:**

- `m_F` = `2143.934303`
- `payload_mass` = `1100`
- `m_MTO` = `10297.779318`

**Result:**

`useful_load_ratio` = `0.315013`

---

### 12. T_TO_base

Базовая взлётная тяга.

**Formula:**

$$
T_{TO} = m_{MTO} \cdot g \cdot P_{0,opt}
$$

**Values:**

- `m_MTO` = `10297.779318`
- `g` = `9.80665`
- `P0_optimal` = `0.437488`

**Result:**

`T_TO_base` = `44180.427096` `N`

---

### 13. S_W

Площадь крыла по взлётной массе и нагрузке на крыло.

**Formula:**

$$
S_W = \frac{m_{MTO}}{p_{0,opt}}
$$

**Values:**

- `m_MTO` = `10297.779318`
- `p0_optimal` = `705.974274`

**Result:**

`S_W` = `14.586621` `m²`

---

### 14. iteration_1.fuel_mass

Fuel mass for current component-mass iteration.

**Formula:**

$$
m_F = m_0 \cdot \bar{m}_F
$$

**Values:**

- `m0` = `10297.779318`
- `fuel_mass_ratio` = `0.208194`
- `iteration` = `1`

**Result:**

`iteration_1.fuel_mass` = `2143.934303` `kg`

---

### 15. iteration_1.wing_span

Wing span used in component wing mass formulas.

**Formula:**

$$
l = \sqrt{S_W \cdot \lambda}
$$

**Values:**

- `S_W` = `14.586621`
- `lambda_wing` = `9.2`
- `iteration` = `1`

**Result:**

`iteration_1.wing_span` = `11.584339` `m`

---

### 16. iteration_1.wing_mass_1

First wing mass estimate.

**Formula:**

$$
m_{wing,1} = 0.002 \cdot k_m \cdot m_0 \cdot n_p \cdot \left(0.6 \cdot \left(\frac{l}{2}\right)^2 + 1\right) + 3 \cdot S_W
$$

**Values:**

- `k_m` = `1`
- `m0` = `10297.779318`
- `n_p` = `3.2`
- `wing_span` = `11.584339`
- `S_W` = `14.586621`
- `iteration` = `1`

**Result:**

`iteration_1.wing_mass_1` = `1436.318659` `kg`

---

### 17. iteration_1.wing_mass_2

Second wing mass estimate.

**Formula:**

$$
m_{wing,2} = 0.001 \cdot k_m \cdot m_0 \cdot n_p \cdot \lambda \cdot (\eta + 3) \cdot \sqrt{\frac{S_W}{\eta}} \cdot \sqrt{\bar{c}}
$$

**Values:**

- `k_m` = `1`
- `m0` = `10297.779318`
- `n_p` = `3.2`
- `lambda_wing` = `9.2`
- `eta` = `2.5`
- `S_W` = `14.586621`
- `c_bar` = `0.12`
- `iteration` = `1`

**Result:**

`iteration_1.wing_mass_2` = `1395.217924` `kg`

---

### 18. iteration_1.wing_mass

Mean wing mass estimate.

**Formula:**

$$
m_{wing} = \frac{m_{wing,1} + m_{wing,2}}{2}
$$

**Values:**

- `m_wing_1` = `1436.318659`
- `m_wing_2` = `1395.217924`
- `iteration` = `1`

**Result:**

`iteration_1.wing_mass` = `1415.768292` `kg`

---

### 19. iteration_1.G0_for_fuselage

Aircraft weight-like value used by fuselage empirical formula.

**Formula:**

$$
G_0 = m_0 \cdot g
$$

**Values:**

- `m0` = `10297.779318`
- `g` = `9.80665`
- `iteration` = `1`

**Result:**

`iteration_1.G0_for_fuselage` = `100986.717546` `daN`

---

### 20. iteration_1.fuselage_mass

Fuselage mass empirical estimate.

**Formula:**

$$
m_f = \frac{0.584 \cdot k_{cx} \cdot G_0^{0.771}}{g}
$$

**Values:**

- `G0` = `100986.717546`
- `k_cx` = `1`
- `g` = `9.80665`
- `iteration` = `1`

**Result:**

`iteration_1.fuselage_mass` = `429.714406` `kg`

---

### 21. iteration_1.V_cruise_kmh

Cruise speed conversion for tail mass formulas.

**Formula:**

$$
V_{cruise,kmh} = 3.6 \cdot V_{cruise,mps}
$$

**Values:**

- `V_cruise_mps` = `185`
- `iteration` = `1`

**Result:**

`iteration_1.V_cruise_kmh` = `666` `km/h`

---

### 22. iteration_1.wing_area_for_tail

Wing area used to estimate tail areas.

**Formula:**

$$
S_W = \frac{m_0 \cdot g}{p_0}
$$

**Values:**

- `m0` = `10297.779318`
- `g` = `9.80665`
- `p0_optimal` = `705.974274`
- `iteration` = `1`

**Result:**

`iteration_1.wing_area_for_tail` = `143.045889` `m²`

---

### 23. iteration_1.horizontal_tail_area

Horizontal tail area.

**Formula:**

$$
S_{ht} = k_{ht} \cdot S_W
$$

**Values:**

- `k_horizontal_tail` = `0.25`
- `wing_area` = `143.045889`
- `iteration` = `1`

**Result:**

`iteration_1.horizontal_tail_area` = `35.761472` `m²`

---

### 24. iteration_1.vertical_tail_area

Vertical tail area.

**Formula:**

$$
S_{vt} = k_{vt} \cdot S_W
$$

**Values:**

- `k_vertical_tail` = `0.15`
- `wing_area` = `143.045889`
- `iteration` = `1`

**Result:**

`iteration_1.vertical_tail_area` = `21.456883` `m²`

---

### 25. iteration_1.horizontal_tail_mass

Horizontal tail mass estimate.

**Formula:**

$$
m_{ht} = 7.2 \cdot S_{ht}^{1.2} \cdot \left(0.4 + \frac{V_{cruise} + 113}{935}\right)
$$

**Values:**

- `S_ht` = `35.761472`
- `V_cruise_kmh` = `666`
- `iteration` = `1`

**Result:**

`iteration_1.horizontal_tail_mass` = `649.30487` `kg`

---

### 26. iteration_1.vertical_tail_mass

Vertical tail mass estimate.

**Formula:**

$$
m_{vt} = 6.8 \cdot S_{vt}^{1.2} \cdot \left(0.4 + \frac{7 \cdot (V_{cruise} + 113)}{1100}\right)
$$

**Values:**

- `S_vt` = `21.456883`
- `V_cruise_kmh` = `666`
- `iteration` = `1`

**Result:**

`iteration_1.vertical_tail_mass` = `1443.220324` `kg`

---

### 27. iteration_1.tail_mass

Total tail mass.

**Formula:**

$$
m_{tail} = m_{ht} + m_{vt}
$$

**Values:**

- `m_ht` = `649.30487`
- `m_vt` = `1443.220324`
- `iteration` = `1`

**Result:**

`iteration_1.tail_mass` = `2092.525194` `kg`

---

### 28. iteration_1.q_dynamic

Dynamic pressure at cruise.

**Formula:**

$$
q = \frac{\rho \cdot V^2}{2}
$$

**Values:**

- `rho` = `0.45`
- `V_cruise` = `185`
- `iteration` = `1`

**Result:**

`iteration_1.q_dynamic` = `7700.625` `Pa`

---

### 29. iteration_1.k_ind

Induced drag factor.

**Formula:**

$$
k_{ind} = \frac{1}{\pi \cdot e \cdot \lambda}
$$

**Values:**

- `e` = `0.82`
- `lambda_wing` = `9.2`
- `iteration` = `1`

**Result:**

`iteration_1.k_ind` = `0.042194`

---

### 30. iteration_1.specific_power

Specific power-like value for powerplant mass formulas.

**Formula:**

$$
\bar{N}_0 = \frac{1}{\eta_v} \cdot \left(\frac{q \cdot C_{x0}}{p_0 \cdot V} + \frac{p_0 \cdot k_{ind}}{q \cdot V}\right)
$$

**Values:**

- `propeller_efficiency` = `0.8`
- `q_dynamic` = `7700.625`
- `C_x0` = `0.028`
- `p0_optimal` = `705.974274`
- `V_cruise` = `185`
- `k_ind` = `0.042194`
- `iteration` = `1`

**Result:**

`iteration_1.specific_power` = `0.00209`

---

### 31. iteration_1.total_power

Total required power-like value.

**Formula:**

$$
N_0 = \bar{N}_0 \cdot m_0
$$

**Values:**

- `specific_power` = `0.00209`
- `m0` = `10297.779318`
- `iteration` = `1`

**Result:**

`iteration_1.total_power` = `21.520033`

---

### 32. iteration_1.gamma_engine

Engine specific mass coefficient.

**Formula:**

$$
\gamma_{engine} = 0.9 - 0.012 \cdot \sqrt{N_0}
$$

**Values:**

- `engine_type` = `ПД воздушного охлаждения`
- `total_power` = `21.520033`
- `iteration` = `1`

**Result:**

`iteration_1.gamma_engine` = `0.844332`

---

### 33. iteration_1.powerplant_mass

Powerplant mass estimate.

**Formula:**

$$
m_{su} = N_0 \cdot (\gamma_{engine} + k_{su})
$$

**Values:**

- `total_power` = `21.520033`
- `gamma_engine` = `0.844332`
- `k_su` = `0.55`
- `iteration` = `1`

**Result:**

`iteration_1.powerplant_mass` = `30.006079` `kg`

---

### 34. iteration_1.landing_gear_base_weight

Base landing gear weight estimate.

**Formula:**

$$
G_{gear,base} = k_{mat} \cdot k_{fair} \cdot (11.7 + 6h) \cdot 10^{-3} \cdot G_0
$$

**Values:**

- `k_material` = `1`
- `k_fairing` = `1`
- `h` = `1`
- `G0` = `10098.671755`
- `iteration` = `1`

**Result:**

`iteration_1.landing_gear_base_weight` = `178.74649` `daN`

---

### 35. iteration_1.landing_gear_mass

Landing gear mass estimate.

**Formula:**

$$
m_{gear} = \frac{G_{gear,total} \cdot 10}{g}
$$

**Values:**

- `landing_gear_type` = `колёсное с тормозами`
- `G_gear_total_daN` = `404.735829`
- `g` = `9.80665`
- `iteration` = `1`

**Result:**

`iteration_1.landing_gear_mass` = `412.715687` `kg`

---

### 36. iteration_1.battery_mass

Battery mass is zero for non-electric powerplant.

**Formula:**

$$
m_{battery} = 0
$$

**Values:**

- `engine_type` = `ПД воздушного охлаждения`
- `iteration` = `1`

**Result:**

`iteration_1.battery_mass` = `0` `kg`

---

### 37. iteration_1.equipment_and_control_mass

Equipment and control mass estimate.

**Formula:**

$$
m_{eq} = \frac{0.00635 \cdot G_0^{1.37} \cdot 10}{g}
$$

**Values:**

- `G0_daN` = `10098.671755`
- `g` = `9.80665`
- `iteration` = `1`

**Result:**

`iteration_1.equipment_and_control_mass` = `1981.960892` `kg`

---

### 38. iteration_1.additional_mass

Additional placeholder mass.

**Formula:**

$$
m_{add} = m_0 \cdot \bar{m}_{add}
$$

**Values:**

- `m0` = `10297.779318`
- `additional_mass_ratio` = `0`
- `iteration` = `1`

**Result:**

`iteration_1.additional_mass` = `0` `kg`

---

### 39. component_mass_iteration

Iterative component mass refinement.

**Formula:**

$$
m_{0,new} = m_{payload} + m_F + m_{wing} + m_{fuselage} + m_{tail} + m_{powerplant} + m_{gear} + m_{battery} + m_{equipment} + m_{additional}
$$

**Values:**

- `initial_m0` = `10297.779318`
- `tolerance` = `0.05`
- `max_iterations` = `30`
- `iterations` = `8`
- `converged` = `True`
- `relative_delta` = `0.048254`

**Result:**

`component_mass_iteration` = `{"final_m0": 6294.07226289026, "component_masses": {"payload": 1100.0, "fuel": 1376.8237899840317, "wing": 917.0280022615528, "fuselage": 305.4155071226302, "tail": 1229.9032856492372, "powerplant": 19.42256378497859, "landing_gear": 265.04393124851, "battery": 0.0, "equipment_and_control": 1080.4351828393203, "additional": 0.0, "operating_empty_mass": 3817.248472906229, "total_mass": 6294.07226289026}}` `kg`

---

## geometry

### 1. wing_span

Размах крыла.

**Formula:**

$$
l_{wing} = \sqrt{S_{wing} \cdot \lambda_{wing}}
$$

**Values:**

- `S_wing` = `8.915441`
- `lambda_wing` = `9.2`

**Result:**

`wing_span` = `9.056603` `m`

---

### 2. wing_root_chord

Корневая хорда крыла.

**Formula:**

$$
b_{0,wing} = \frac{2S_{wing}}{l_{wing}\left(1 + \frac{1}{\eta_{wing}}\right)}
$$

**Values:**

- `S_wing` = `8.915441`
- `l_wing` = `9.056603`
- `eta_wing` = `2.5`

**Result:**

`wing_root_chord` = `1.406305` `m`

---

### 3. wing_tip_chord

Концевая хорда крыла.

**Formula:**

$$
b_{k,wing} = \frac{b_{0,wing}}{\eta_{wing}}
$$

**Values:**

- `b0_wing` = `1.406305`
- `eta_wing` = `2.5`

**Result:**

`wing_tip_chord` = `0.562522` `m`

---

### 4. wing_le_sweep

Стреловидность крыла по передней кромке.

**Formula:**

$$
\chi_{LE} = \arctan\left(\tan(\chi_{1/4}) + \frac{b_0 - b_k}{2l}\right)
$$

**Values:**

- `sweep_wing_quarter` = `25`
- `b0_wing` = `1.406305`
- `bk_wing` = `0.562522`
- `l_wing` = `9.056603`

**Result:**

`wing_le_sweep` = `27.152902` `deg`

---

### 5. fuselage_length

Длина фюзеляжа.

**Formula:**

$$
L_f = k_f \cdot l_{wing}
$$

**Values:**

- `k_fuselage` = `1.2`
- `l_wing` = `9.056603`

**Result:**

`fuselage_length` = `10.867924` `m`

---

### 6. fuselage_diameter

Диаметр фюзеляжа.

**Formula:**

$$
d_f = \frac{L_f}{\lambda_f}
$$

**Values:**

- `L_fuselage` = `10.867924`
- `lambda_fuselage` = `9`

**Result:**

`fuselage_diameter` = `1.207547` `m`

---

### 7. fuselage_radius

Радиус фюзеляжа.

**Formula:**

$$
r_f = \frac{d_f}{2}
$$

**Values:**

- `d_fuselage` = `1.207547`

**Result:**

`fuselage_radius` = `0.603774` `m`

---

### 8. wing_vertical_position

Вертикальное положение крыла относительно фюзеляжа.

**Formula:**

$$
y_{wing} = \begin{cases}\frac{d_f}{2}, & \text{high wing} \\ 0, & \text{mid wing} \\ -\frac{d_f}{2}, & \text{low wing}\end{cases}
$$

**Values:**

- `wing_scheme` = `mid`
- `d_fuselage` = `1.207547`

**Result:**

`wing_vertical_position` = `0` `m`

---

### 9. horizontal_tail_area

Площадь горизонтального оперения.

**Formula:**

$$
S_{ht} = k_{ht} \cdot S_{wing}
$$

**Values:**

- `k_horizontal_tail` = `0.25`
- `S_wing` = `8.915441`

**Result:**

`horizontal_tail_area` = `2.22886` `m²`

---

### 10. horizontal_tail_span

Размах горизонтального оперения.

**Formula:**

$$
l_{ht} = \sqrt{S_{ht} \cdot \lambda_{ht}}
$$

**Values:**

- `S_ht` = `2.22886`
- `lambda_horizontal_tail` = `4`

**Result:**

`horizontal_tail_span` = `2.985874` `m`

---

### 11. horizontal_tail_root_chord

Корневая хорда горизонтального оперения.

**Formula:**

$$
b_{0,ht} = \frac{2S_{ht}}{l_{ht}\left(1 + \frac{1}{\eta_{ht}}\right)}
$$

**Values:**

- `S_ht` = `2.22886`
- `l_ht` = `2.985874`
- `eta_horizontal_tail` = `3`

**Result:**

`horizontal_tail_root_chord` = `1.119703` `m`

---

### 12. horizontal_tail_tip_chord

Концевая хорда горизонтального оперения.

**Formula:**

$$
b_{k,ht} = \frac{b_{0,ht}}{\eta_{ht}}
$$

**Values:**

- `b0_ht` = `1.119703`
- `eta_horizontal_tail` = `3`

**Result:**

`horizontal_tail_tip_chord` = `0.373234` `m`

---

### 13. horizontal_tail_le_sweep

Стреловидность горизонтального оперения по передней кромке.

**Formula:**

$$
\chi_{LE,ht} = \arctan\left(\tan(\chi_{1/4,ht}) + \frac{b_{0,ht} - b_{k,ht}}{2l_{ht}}\right)
$$

**Values:**

- `sweep_horizontal_tail_quarter` = `30`
- `b0_ht` = `1.119703`
- `bk_ht` = `0.373234`
- `l_ht` = `2.985874`

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
- `L_fuselage` = `10.867924`

**Result:**

`horizontal_tail_x_position` = `1.150943` `m`

---

### 15. vertical_tail_area

Площадь вертикального оперения.

**Formula:**

$$
S_{vt} = k_{vt} \cdot S_{wing}
$$

**Values:**

- `k_vertical_tail` = `0.15`
- `S_wing` = `8.915441`

**Result:**

`vertical_tail_area` = `1.337316` `m²`

---

### 16. vertical_tail_span

Размах/высота вертикального оперения.

**Formula:**

$$
l_{vt} = \sqrt{S_{vt} \cdot \lambda_{vt}}
$$

**Values:**

- `S_vt` = `1.337316`
- `lambda_vertical_tail` = `1.5`

**Result:**

`vertical_tail_span` = `1.416324` `m`

---

### 17. vertical_tail_root_chord

Корневая хорда вертикального оперения.

**Formula:**

$$
b_{0,vt} = \frac{2S_{vt}}{l_{vt}\left(1 + \frac{1}{\eta_{vt}}\right)}
$$

**Values:**

- `S_vt` = `1.337316`
- `l_vt` = `1.416324`
- `eta_vertical_tail` = `2`

**Result:**

`vertical_tail_root_chord` = `1.258955` `m`

---

### 18. vertical_tail_tip_chord

Концевая хорда вертикального оперения.

**Formula:**

$$
b_{k,vt} = \frac{b_{0,vt}}{\eta_{vt}}
$$

**Values:**

- `b0_vt` = `1.258955`
- `eta_vertical_tail` = `2`

**Result:**

`vertical_tail_tip_chord` = `0.629477` `m`

---

### 19. vertical_tail_le_sweep

Стреловидность вертикального оперения по передней кромке.

**Formula:**

$$
\chi_{LE,vt} = \arctan\left(\tan(\chi_{1/4,vt}) + \frac{b_{0,vt} - b_{k,vt}}{2l_{vt}}\right)
$$

**Values:**

- `sweep_vertical_tail_quarter` = `35`
- `b0_vt` = `1.258955`
- `bk_vt` = `0.629477`
- `l_vt` = `1.416324`

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
- `L_fuselage` = `10.867924`

**Result:**

`vertical_tail_x_position` = `1.150943` `m`

---
