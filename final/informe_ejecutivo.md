# ¿Volverá a ganar El Matador? Informe ejecutivo

**Caso CD-726-017** · Responsable: jorgebb01 · Cifras generadas por `uv run ufcpeleas pipeline` · Cada número lleva su ID de origen `[C-xxx]`, que se rastrea en `final/cifras.csv` y `final/linaje.csv`.

## 1. Respuesta

**Topuria es favorito en los dos escenarios.** La probabilidad de que gane su próxima pelea, con fecha supuesta el 15 de febrero de 2027 (D-28), es:

| Escenario | **Mercado (modelo elegido)** | Modelo historial (B) (IC95) | Modelo combinado (C) (IC95) |
|---|---|---|---|
| Revancha con Justin Gaethje | **68,9 % [C-049]** | 69,6 % [C-052] (63,5 % [C-053] – 76,0 % [C-054]) | 71,8 % [C-055] (65,0 % [C-056] – 79,1 % [C-057]) |
| Contra Paddy Pimblett | **79,8 % [C-058]** | 57,9 % [C-061] (50,2 % [C-062] – 65,5 % [C-063]) | 80,9 % [C-064] (74,7 % [C-065] – 86,1 % [C-066]) |

- **El rival cambia la probabilidad en unos 10,9 [C-058 − C-049] puntos** a favor del escenario Pimblett. Gaethje ya le ganó, es el campeón y llega con una racha de 3 [C-069] victorias; Pimblett llega con 1 [C-072] y es más joven (32,1 [C-071] años frente a 38,3 [C-068]).
- **Elegimos el mercado** (la cuota sin el margen de la casa) porque ningún modelo propio lo supera. En las 892 [C-042] peleas de prueba (2025-2026), su log-loss es 0,586 [C-016]. El modelo combinado empata (0,587 [C-032]; diferencia 0,001 [C-038], IC95 de -0,006 [C-039] a 0,009 [C-040]) y el de historial es claramente peor (0,646 [C-022]). El mercado acierta el ganador en el 69,6 % [C-020] de las peleas. Modelo elegido según la regla de D-27: A_mercado [C-043].
- **La probabilidad de mercado es una estimación puntual:** cada escenario tiene una sola línea vigente. Como referencia de incertidumbre se usa el intervalo del modelo combinado (D-33).

## 2. Cómo se obtuvo

- **Datos:** historial de peleas de ufcstats (Kaggle `scarekrow/ufc-data` v21, F-01, hasta el 17 de octubre de 2026, incluida la derrota ante Gaethje), cuotas de Kaggle (`archangel0x01` v3 y `jerzyszocik` v273, F-04 a F-07) y cuotas añadidas a mano con URL, fecha y captura de la página (F-02, F-03). Los archivos crudos están intactos y verificados por SHA-256 en cada ejecución.
- **Modelos:** regresión logística sobre diferencias entre los dos peleadores (historial previo a cada pelea, edad, altura y alcance), con y sin la cuota. Entrenamiento 2021-2023, validación 2024 y prueba 2025-2026, sin mezclar el orden temporal.
- **Escenarios:** el historial de cada peleador se calcula a la fecha supuesta, con la derrota de Topuria (racha -1 [C-073]) y la victoria de Pimblett sobre Saint-Denis. La cuota de la revancha es la línea vigente de BetOnline.ag (-250/+210; F-07 y M-0109 a M-0114); la de Pimblett, -500/+375 (M-0172, M-0173; sin margen, 79,8 % [C-158]), citada por la prensa (D-31).

## 3. ¿La derrota ante Gaethje es un dato atípico o una señal de cambio?

**Fue un resultado poco probable, pero no excepcional.** Antes de la pelea el mercado le daba a Topuria un 78,9 % [C-002] (cierre de 5 [C-003] casas) y nuestros modelos, entrenados solo con peleas anteriores, un 80,0 % [C-087] (B) y un 82,3 % [C-088] (C). El "6 a 1" del caso (≈ 86 %) corresponde a líneas de mayo, no al cierre (D-09). Desde 2021, los favoritos con entre el 75 % y el 85 % de probabilidad pierden el 15,1 % [C-089] de las veces.

**Por asaltos, la pelea muestra desgaste a partir del tercero:**

| Topuria | R1 | R2 | R3 | R4 | Media por asalto en sus 9 peleas previas |
|---|---|---|---|---|---|
| Golpes significativos conectados | 29 [C-094] | 44 [C-095] | 7 [C-096] | 17 [C-097] | 20,2 [C-099] |
| Golpes significativos recibidos | 32 [C-106] | 12 [C-107] | 22 [C-108] | 25 [C-109] | 16,1 [C-111] |
| Golpes a la cabeza recibidos | 30 [C-118] | 11 [C-119] | 19 [C-120] | 19 [C-121] | 8,9 [C-123] |
| Segundos controlado por Gaethje | 0 [C-148] | 0 [C-149] | 47 [C-150] | 45 [C-151] | 15,1 [C-153] |

Dominó el segundo asalto (1 [C-125] derribo con golpe, 122 [C-143] s de control), pero en el tercero conectó solo 7 [C-096] de 15 [C-102] golpes intentados y en el tercero y el cuarto fue controlado. Recibió más del doble de golpes a la cabeza que su media.

**La inactividad no explica la derrota por sí sola.** Topuria llegaba con 351 [C-091] días sin pelear, pero en el conjunto de la UFC, los peleadores con 300 días o más de inactividad no rinden por debajo de lo que espera el mercado (residuo medio 0,001 [C-092] frente a 0,002 [C-093]).

**Conclusión:** los datos son compatibles con una derrota dentro de lo esperable más un bajón físico visible desde el tercer asalto. Una sola pelea no basta para confirmar un cambio estructural. El mercado lo recoge: la revancha baja a 68,9 % [C-049], frente al 78,9 % [C-002] de la primera pelea.

## 4. Sesgos de los datos con corte anterior a 2026 y cómo se corrigieron

1. **Falta la derrota ante Gaethje.** Se eligió un dataset con corte el 17 de octubre de 2026, citado por versión (v21) para que no cambie (D-05).
2. **Fuga temporal.** Las estadísticas de carrera y los rankings de Kaggle son una foto actual del peleador. Se descartaron y el historial se recalculó con solo las peleas anteriores a cada combate (D-03, D-06); un test lo comprueba.
3. **Cuotas vacías o antiguas.** El dataset principal no tiene cuotas. Se añadieron dos datasets de Kaggle y cuotas manuales. La cobertura de cierre es del 96,7 % [C-008] desde 2021 y del 100,0 % [C-010] en las peleas de Topuria. 3 [C-011] cuotas de Topuria vienen de una carga histórica sin casa identificada: quitarlas cambia sus probabilidades como máximo 0,0005 [C-077], menos de una décima de punto (D-18). En cambio, sí pesan en su historial: Topuria ganó 2,4 [C-083] peleas más de las que esperaba el mercado, pero sin esas 3 cuotas el exceso baja a 1,0 [C-085]. La línea Topuria–Pimblett de diciembre de 2025 es anterior a la derrota; con ella la probabilidad sería 84,4 % [C-160] (4,5 [C-161] puntos más) y se usa solo como sensibilidad (D-31).
4. **Solo peleas UFC.** Topuria llegó invicto de fuera de la UFC y ese historial no cuenta en las variables.

**Cómo se mantiene la trazabilidad:** los archivos crudos no se modifican. Lo añadido a mano va en `manual/` con URL, fecha de consulta y captura con hash. Cada transformación queda en `bitacora.csv` (T-xx automáticas, T-00 a T-06 e I-xx manuales). Los 35 criterios están escritos y aprobados en `decisiones.md`.

## 5. Si el auditor encuentra un error en T-07, ¿qué cifras cambian?

`uv run ufcpeleas linaje T-07` lo responde a partir de `final/linaje.csv`. **Cambiarían 161 de las 163 cifras**: todas salvo las que solo dependen de la línea de cuota Topuria–Pimblett, porque T-07 es la carga del historial de peleas del que sale todo lo demás. Por comparación, un error en las cuotas manuales (F-02) afectaría a 96 cifras y uno en T-23 (cuotas de los escenarios) a 43. El linaje es conservador: puede marcar como afectada una cifra que en realidad no cambie, pero no deja fuera ninguna que sí cambie.

## 6. Supuestos y limitaciones

- La pelea se supone el 15 de febrero de 2027 y el rival no está confirmado.
- La cuota de Pimblett procede de prensa (Heavy, 17 de octubre de 2026) que cita el agregador FightOdds.io, sin casa ni fecha conocidas.
- La probabilidad de mercado no tiene intervalo propio (D-33) y depende de una sola línea por escenario.
- El modelo no tiene en cuenta lesiones, campamento de entrenamiento ni categoría de peso (las dos peleas serían en peso ligero).

## Anexo: cifras citadas

| ID | Valor | Descripción | Archivo | Localizador | Transformación |
|---|---|---|---|---|---|
| C-002 | 0.788653 | Probabilidad de mercado (cierre, sin margen) de Topuria vs Gaethje 2026-06-14 | `final/dataset_analitico.csv` | id_fila = 7208e40818401e88-f2, columna p_cierre_peleador | T-19 |
| C-003 | 5.0 | Casas promediadas en la cuota de cierre de Topuria vs Gaethje | `final/dataset_analitico.csv` | id_fila = 7208e40818401e88-f2, columna cuota_n_casas | T-19 |
| C-008 | 96.67 | Cobertura de cuota de cierre (%), desde 2021-01-01 | `final/cobertura_cuotas.csv` | ambito = desde 2021-01-01, columna pct_con_cuota | T-20 |
| C-010 | 100.0 | Cobertura de cuota de cierre (%), Ilia Topuria | `final/cobertura_cuotas.csv` | ambito = Ilia Topuria, columna pct_con_cuota | T-20 |
| C-011 | 3 | Peleas con cuota de la carga histórica zewnetrzne de F-07 (D-18), Ilia Topuria | `final/cobertura_cuotas.csv` | ambito = Ilia Topuria, columna carga_historica_f07 | T-20 |
| C-016 | 0.585857 | Log-loss en test, modelo A_mercado | `final/modelo_metricas.csv` | modelo = A_mercado, columna log_loss | T-26 |
| C-020 | 0.696188 | Accuracy en test, modelo A_mercado | `final/modelo_metricas.csv` | modelo = A_mercado, columna accuracy | T-26 |
| C-022 | 0.646378 | Log-loss en test, modelo B_historial | `final/modelo_metricas.csv` | modelo = B_historial, columna log_loss | T-26 |
| C-032 | 0.586929 | Log-loss en test, modelo C_combinado | `final/modelo_metricas.csv` | modelo = C_combinado, columna log_loss | T-26 |
| C-038 | 0.001072 | Diferencia de log-loss con el mercado, modelo C_combinado | `final/modelo_metricas.csv` | modelo = C_combinado, columna dif_log_loss_vs_mercado | T-26 |
| C-039 | -0.006226 | Diferencia de log-loss con el mercado, IC95 inferior, modelo C_combinado | `final/modelo_metricas.csv` | modelo = C_combinado, columna dif_ic95_inf | T-26 |
| C-040 | 0.008716 | Diferencia de log-loss con el mercado, IC95 superior, modelo C_combinado | `final/modelo_metricas.csv` | modelo = C_combinado, columna dif_ic95_sup | T-26 |
| C-042 | 892 | Peleas en el conjunto de test (2025-2026) | `final/modelo_metricas.csv` | columna peleas_test | T-26 |
| C-043 | A_mercado | Modelo elegido (regla de T-26) | `final/modelo_metricas.csv` | columna elegido = True | T-26 |
| C-049 | 0.688889 | Probabilidad de victoria de Topuria, escenario revancha_gaethje (2027-02-15), modelo A_mercado | `final/escenarios.csv` | escenario = revancha_gaethje, modelo = A_mercado, columna p_topuria | T-29 |
| C-052 | 0.696201 | Probabilidad de victoria de Topuria, escenario revancha_gaethje (2027-02-15), modelo B_historial | `final/escenarios.csv` | escenario = revancha_gaethje, modelo = B_historial, columna p_topuria | T-29 |
| C-053 | 0.635299 | Límite inferior del intervalo, escenario revancha_gaethje (2027-02-15), modelo B_historial | `final/escenarios.csv` | escenario = revancha_gaethje, modelo = B_historial, columna ic_inf | T-29 |
| C-054 | 0.760104 | Límite superior del intervalo, escenario revancha_gaethje (2027-02-15), modelo B_historial | `final/escenarios.csv` | escenario = revancha_gaethje, modelo = B_historial, columna ic_sup | T-29 |
| C-055 | 0.718494 | Probabilidad de victoria de Topuria, escenario revancha_gaethje (2027-02-15), modelo C_combinado | `final/escenarios.csv` | escenario = revancha_gaethje, modelo = C_combinado, columna p_topuria | T-29 |
| C-056 | 0.649799 | Límite inferior del intervalo, escenario revancha_gaethje (2027-02-15), modelo C_combinado | `final/escenarios.csv` | escenario = revancha_gaethje, modelo = C_combinado, columna ic_inf | T-29 |
| C-057 | 0.791473 | Límite superior del intervalo, escenario revancha_gaethje (2027-02-15), modelo C_combinado | `final/escenarios.csv` | escenario = revancha_gaethje, modelo = C_combinado, columna ic_sup | T-29 |
| C-058 | 0.798319 | Probabilidad de victoria de Topuria, escenario pimblett (2027-02-15), modelo A_mercado | `final/escenarios.csv` | escenario = pimblett, modelo = A_mercado, columna p_topuria | T-29 |
| C-061 | 0.579418 | Probabilidad de victoria de Topuria, escenario pimblett (2027-02-15), modelo B_historial | `final/escenarios.csv` | escenario = pimblett, modelo = B_historial, columna p_topuria | T-29 |
| C-062 | 0.501983 | Límite inferior del intervalo, escenario pimblett (2027-02-15), modelo B_historial | `final/escenarios.csv` | escenario = pimblett, modelo = B_historial, columna ic_inf | T-29 |
| C-063 | 0.655179 | Límite superior del intervalo, escenario pimblett (2027-02-15), modelo B_historial | `final/escenarios.csv` | escenario = pimblett, modelo = B_historial, columna ic_sup | T-29 |
| C-064 | 0.809135 | Probabilidad de victoria de Topuria, escenario pimblett (2027-02-15), modelo C_combinado | `final/escenarios.csv` | escenario = pimblett, modelo = C_combinado, columna p_topuria | T-29 |
| C-065 | 0.74655 | Límite inferior del intervalo, escenario pimblett (2027-02-15), modelo C_combinado | `final/escenarios.csv` | escenario = pimblett, modelo = C_combinado, columna ic_inf | T-29 |
| C-066 | 0.860594 | Límite superior del intervalo, escenario pimblett (2027-02-15), modelo C_combinado | `final/escenarios.csv` | escenario = pimblett, modelo = C_combinado, columna ic_sup | T-29 |
| C-068 | 38.253251 | Edad de Justin Gaethje a 2027-02-15 | `interim/t24_escenarios_variables.csv` | escenario = revancha_gaethje, columna rival_edad | T-24 |
| C-069 | 3 | Racha de Justin Gaethje a 2027-02-15 | `interim/t24_escenarios_variables.csv` | escenario = revancha_gaethje, columna rival_hist_racha | T-24 |
| C-071 | 32.117728 | Edad de Paddy Pimblett a 2027-02-15 | `interim/t24_escenarios_variables.csv` | escenario = pimblett, columna rival_edad | T-24 |
| C-072 | 1 | Racha de Paddy Pimblett a 2027-02-15 | `interim/t24_escenarios_variables.csv` | escenario = pimblett, columna rival_hist_racha | T-24 |
| C-073 | -1 | Racha de Topuria a 2027-02-15 | `interim/t24_escenarios_variables.csv` | columna hist_racha | T-24 |
| C-077 | 0.000484 | Cambio de la probabilidad de Topuria, escenario pimblett, modelo C_combinado, variante sin_3_peleas_topuria | `final/sensibilidad_d18.csv` | variante = sin_3_peleas_topuria, escenario = pimblett, modelo = C_combinado, columna dif_vs_base | T-30 |
| C-083 | 2.408988 | Victorias de Topuria menos las esperadas por el mercado (historial_cuotas_10_peleas) | `final/sensibilidad_d18.csv` | variante = historial_cuotas_10_peleas, columna dif_vs_base | T-30 |
| C-085 | 0.952856 | Victorias de Topuria menos las esperadas por el mercado (historial_cuotas_sin_3) | `final/sensibilidad_d18.csv` | variante = historial_cuotas_sin_3, columna dif_vs_base | T-30 |
| C-087 | 0.800101 | Pregunta 2: p_topuria_B_historial (entrenado con peleas de 2021-01-01 a 2026-06-06 (antes de la pelea)) | `final/pregunta2_prepelea.csv` | indicador = p_topuria_B_historial | T-31 |
| C-088 | 0.822718 | Pregunta 2: p_topuria_C_combinado (entrenado con peleas de 2021-01-01 a 2026-06-06 (antes de la pelea)) | `final/pregunta2_prepelea.csv` | indicador = p_topuria_C_combinado | T-31 |
| C-089 | 0.150776 | Pregunta 2: tasa_derrota_favoritos_075_085 (peleas desde 2021-01-01 con favorito de mercado entre 0,75 y 0,85; p media del favorito 0.7927) | `final/pregunta2_prepelea.csv` | indicador = tasa_derrota_favoritos_075_085 | T-31 |
| C-091 | 351.0 | Pregunta 2: topuria_dias_inactivo_antes_gaethje (hist_dias_desde_ultima (T-10)) | `final/pregunta2_prepelea.csv` | indicador = topuria_dias_inactivo_antes_gaethje | T-31 |
| C-092 | 0.000669 | Pregunta 2: residuo_medio_inactividad_300_o_mas (victoria - p mercado; IC95 bootstrap [-0.0283, 0.0295] (exploratorio)) | `final/pregunta2_prepelea.csv` | indicador = residuo_medio_inactividad_300_o_mas | T-31 |
| C-093 | 0.001802 | Pregunta 2: residuo_medio_inactividad_menos_300 (victoria - p mercado; IC95 bootstrap [-0.0125, 0.0156] (exploratorio)) | `final/pregunta2_prepelea.csv` | indicador = residuo_medio_inactividad_menos_300 | T-31 |
| C-094 | 29.0 | Topuria por asalto: golpes_sig_conectados, R1_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_conectados, columna R1_vs_gaethje | T-32 |
| C-095 | 44.0 | Topuria por asalto: golpes_sig_conectados, R2_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_conectados, columna R2_vs_gaethje | T-32 |
| C-096 | 7.0 | Topuria por asalto: golpes_sig_conectados, R3_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_conectados, columna R3_vs_gaethje | T-32 |
| C-097 | 17.0 | Topuria por asalto: golpes_sig_conectados, R4_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_conectados, columna R4_vs_gaethje | T-32 |
| C-099 | 20.25 | Topuria por asalto: golpes_sig_conectados, media_por_asalto_previa | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_conectados, columna media_por_asalto_previa | T-32 |
| C-102 | 15.0 | Topuria por asalto: golpes_sig_intentados, R3_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_intentados, columna R3_vs_gaethje | T-32 |
| C-106 | 32.0 | Topuria por asalto: golpes_sig_recibidos, R1_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_recibidos, columna R1_vs_gaethje | T-32 |
| C-107 | 12.0 | Topuria por asalto: golpes_sig_recibidos, R2_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_recibidos, columna R2_vs_gaethje | T-32 |
| C-108 | 22.0 | Topuria por asalto: golpes_sig_recibidos, R3_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_recibidos, columna R3_vs_gaethje | T-32 |
| C-109 | 25.0 | Topuria por asalto: golpes_sig_recibidos, R4_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_recibidos, columna R4_vs_gaethje | T-32 |
| C-111 | 16.15 | Topuria por asalto: golpes_sig_recibidos, media_por_asalto_previa | `final/pregunta2_por_asalto.csv` | metrica = golpes_sig_recibidos, columna media_por_asalto_previa | T-32 |
| C-118 | 30.0 | Topuria por asalto: golpes_cabeza_recibidos, R1_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_cabeza_recibidos, columna R1_vs_gaethje | T-32 |
| C-119 | 11.0 | Topuria por asalto: golpes_cabeza_recibidos, R2_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_cabeza_recibidos, columna R2_vs_gaethje | T-32 |
| C-120 | 19.0 | Topuria por asalto: golpes_cabeza_recibidos, R3_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_cabeza_recibidos, columna R3_vs_gaethje | T-32 |
| C-121 | 19.0 | Topuria por asalto: golpes_cabeza_recibidos, R4_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = golpes_cabeza_recibidos, columna R4_vs_gaethje | T-32 |
| C-123 | 8.9 | Topuria por asalto: golpes_cabeza_recibidos, media_por_asalto_previa | `final/pregunta2_por_asalto.csv` | metrica = golpes_cabeza_recibidos, columna media_por_asalto_previa | T-32 |
| C-125 | 1.0 | Topuria por asalto: knockdowns_dados, R2_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = knockdowns_dados, columna R2_vs_gaethje | T-32 |
| C-143 | 122.0 | Topuria por asalto: control_seg, R2_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = control_seg, columna R2_vs_gaethje | T-32 |
| C-148 | 0.0 | Topuria por asalto: control_rival_seg, R1_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = control_rival_seg, columna R1_vs_gaethje | T-32 |
| C-149 | 0.0 | Topuria por asalto: control_rival_seg, R2_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = control_rival_seg, columna R2_vs_gaethje | T-32 |
| C-150 | 47.0 | Topuria por asalto: control_rival_seg, R3_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = control_rival_seg, columna R3_vs_gaethje | T-32 |
| C-151 | 45.0 | Topuria por asalto: control_rival_seg, R4_vs_gaethje | `final/pregunta2_por_asalto.csv` | metrica = control_rival_seg, columna R4_vs_gaethje | T-32 |
| C-153 | 15.05 | Topuria por asalto: control_rival_seg, media_por_asalto_previa | `final/pregunta2_por_asalto.csv` | metrica = control_rival_seg, columna media_por_asalto_previa | T-32 |
| C-158 | 0.798319 | Probabilidad sin margen de Topuria en la línea vigente Topuria -500 / Pimblett +375 (D-08, D-31) | `interim/t23_cuotas_futuras.csv` | escenario = pimblett, tipo = vigente_citada_prensa, columna p_topuria | T-23 |
| C-160 | 0.843718 | Sensibilidad D-31: probabilidad de Topuria vs Pimblett con la línea de diciembre de 2025, modelo A_mercado | `final/sensibilidad_d18.csv` | variante = pimblett_linea_dic_2025, modelo = A_mercado, columna p_topuria | T-30 |
| C-161 | 0.045399 | Sensibilidad D-31: diferencia con la línea vigente, modelo A_mercado | `final/sensibilidad_d18.csv` | variante = pimblett_linea_dic_2025, modelo = A_mercado, columna dif_vs_base | T-30 |
