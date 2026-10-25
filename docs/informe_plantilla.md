# ¿Volverá a ganar El Matador? Informe ejecutivo

**Caso CD-726-017** · Responsable: jorgebb01 · Cifras generadas por `uv run ufcpeleas pipeline` · Cada número lleva su ID de origen `[C-xxx]`, que se rastrea en `final/cifras.csv` y `final/linaje.csv`.

## 1. Respuesta

**Topuria es favorito en los dos escenarios.** La probabilidad de que gane su próxima pelea, con fecha supuesta el 15 de febrero de 2027 (D-28), es:

| Escenario | **Mercado (modelo elegido)** | Modelo historial (B) (IC95) | Modelo combinado (C) (IC95) |
|---|---|---|---|
| Revancha con Justin Gaethje | **{{C-049:pct}}** | {{C-052:pct}} ({{C-053:pct}} – {{C-054:pct}}) | {{C-055:pct}} ({{C-056:pct}} – {{C-057:pct}}) |
| Contra Paddy Pimblett | **{{C-058:pct}}** | {{C-061:pct}} ({{C-062:pct}} – {{C-063:pct}}) | {{C-064:pct}} ({{C-065:pct}} – {{C-066:pct}}) |

- **El rival cambia la probabilidad en unos {{DIF:C-058-C-049:pp}} puntos** a favor del escenario Pimblett. Gaethje ya le ganó, es el campeón y llega con una racha de {{C-069:int}} victorias; Pimblett llega con {{C-072:int}} y es más joven ({{C-071:dec1}} años frente a {{C-068:dec1}}).
- **Elegimos el mercado** (la cuota sin el margen de la casa) porque ningún modelo propio lo supera. En las {{C-042:int}} peleas de prueba (2025-2026), su log-loss es {{C-016:dec3}}. El modelo combinado empata ({{C-032:dec3}}; diferencia {{C-038:dec3}}, IC95 de {{C-039:dec3}} a {{C-040:dec3}}) y el de historial es claramente peor ({{C-022:dec3}}). El mercado acierta el ganador en el {{C-020:pct}} de las peleas. Modelo elegido según la regla de D-27: {{C-043:raw}}.
- **La probabilidad de mercado es una estimación puntual:** cada escenario tiene una sola línea vigente. Como referencia de incertidumbre se usa el intervalo del modelo combinado (D-33).

## 2. Cómo se obtuvo

- **Datos:** historial de peleas de ufcstats (Kaggle `scarekrow/ufc-data` v21, F-01, hasta el 17 de octubre de 2026, incluida la derrota ante Gaethje), cuotas de Kaggle (`archangel0x01` v3 y `jerzyszocik` v273, F-04 a F-07) y cuotas añadidas a mano con URL, fecha y captura de la página (F-02, F-03). Los archivos crudos están intactos y verificados por SHA-256 en cada ejecución.
- **Modelos:** regresión logística sobre diferencias entre los dos peleadores (historial previo a cada pelea, edad, altura y alcance), con y sin la cuota. Entrenamiento 2021-2023, validación 2024 y prueba 2025-2026, sin mezclar el orden temporal.
- **Escenarios:** el historial de cada peleador se calcula a la fecha supuesta, con la derrota de Topuria (racha {{C-073:int}}) y la victoria de Pimblett sobre Saint-Denis. La cuota de la revancha es la línea vigente de BetOnline.ag (-250/+210; F-07 y M-0109 a M-0114); la de Pimblett, -500/+375 (M-0172, M-0173; sin margen, {{C-158:pct}}), citada por la prensa (D-31).

## 3. ¿La derrota ante Gaethje es un dato atípico o una señal de cambio?

**Fue un resultado poco probable, pero no excepcional.** Antes de la pelea el mercado le daba a Topuria un {{C-002:pct}} (cierre de {{C-003:int}} casas) y nuestros modelos, entrenados solo con peleas anteriores, un {{C-087:pct}} (B) y un {{C-088:pct}} (C). El "6 a 1" del caso (≈ 86 %) corresponde a líneas de mayo, no al cierre (D-09). Desde 2021, los favoritos con entre el 75 % y el 85 % de probabilidad pierden el {{C-089:pct}} de las veces.

**Por asaltos, la pelea muestra desgaste a partir del tercero:**

| Topuria | R1 | R2 | R3 | R4 | Media por asalto en sus 9 peleas previas |
|---|---|---|---|---|---|
| Golpes significativos conectados | {{C-094:int}} | {{C-095:int}} | {{C-096:int}} | {{C-097:int}} | {{C-099:dec1}} |
| Golpes significativos recibidos | {{C-106:int}} | {{C-107:int}} | {{C-108:int}} | {{C-109:int}} | {{C-111:dec1}} |
| Golpes a la cabeza recibidos | {{C-118:int}} | {{C-119:int}} | {{C-120:int}} | {{C-121:int}} | {{C-123:dec1}} |
| Segundos controlado por Gaethje | {{C-148:int}} | {{C-149:int}} | {{C-150:int}} | {{C-151:int}} | {{C-153:dec1}} |

Dominó el segundo asalto ({{C-125:int}} derribo con golpe, {{C-143:int}} s de control), pero en el tercero conectó solo {{C-096:int}} de {{C-102:int}} golpes intentados y en el tercero y el cuarto fue controlado. Recibió más del doble de golpes a la cabeza que su media.

**La inactividad no explica la derrota por sí sola.** Topuria llegaba con {{C-091:int}} días sin pelear, pero en el conjunto de la UFC, los peleadores con 300 días o más de inactividad no rinden por debajo de lo que espera el mercado (residuo medio {{C-092:dec3}} frente a {{C-093:dec3}}).

**Conclusión:** los datos son compatibles con una derrota dentro de lo esperable más un bajón físico visible desde el tercer asalto. Una sola pelea no basta para confirmar un cambio estructural. El mercado lo recoge: la revancha baja a {{C-049:pct}}, frente al {{C-002:pct}} de la primera pelea.

## 4. Sesgos de los datos con corte anterior a 2026 y cómo se corrigieron

1. **Falta la derrota ante Gaethje.** Se eligió un dataset con corte el 17 de octubre de 2026, citado por versión (v21) para que no cambie (D-05).
2. **Fuga temporal.** Las estadísticas de carrera y los rankings de Kaggle son una foto actual del peleador. Se descartaron y el historial se recalculó con solo las peleas anteriores a cada combate (D-03, D-06); un test lo comprueba.
3. **Cuotas vacías o antiguas.** El dataset principal no tiene cuotas. Se añadieron dos datasets de Kaggle y cuotas manuales. La cobertura de cierre es del {{C-008:pctv}} desde 2021 y del {{C-010:pctv}} en las peleas de Topuria. {{C-011:int}} cuotas de Topuria vienen de una carga histórica sin casa identificada: quitarlas cambia sus probabilidades como máximo {{C-077:dec4}}, menos de una décima de punto (D-18). En cambio, sí pesan en su historial: Topuria ganó {{C-083:dec1}} peleas más de las que esperaba el mercado, pero sin esas 3 cuotas el exceso baja a {{C-085:dec1}}. La línea Topuria–Pimblett de diciembre de 2025 es anterior a la derrota; con ella la probabilidad sería {{C-160:pct}} ({{C-161:pp}} puntos más) y se usa solo como sensibilidad (D-31).
4. **Solo peleas UFC.** Topuria llegó invicto de fuera de la UFC y ese historial no cuenta en las variables.

**Cómo se mantiene la trazabilidad:** los archivos crudos no se modifican. Lo añadido a mano va en `manual/` con URL, fecha de consulta y captura con hash. Cada transformación queda en `bitacora.csv` (T-xx automáticas, T-00 a T-06 e I-xx manuales). Los {{NDEC}} criterios están escritos y aprobados en `decisiones.md`.

## 5. Si el auditor encuentra un error en T-07, ¿qué cifras cambian?

`uv run ufcpeleas linaje T-07` lo responde a partir de `final/linaje.csv`. **Cambiarían {{LINAJE:T-07}} de las {{NCIFRAS}} cifras**: todas salvo las que solo dependen de la línea de cuota Topuria–Pimblett, porque T-07 es la carga del historial de peleas del que sale todo lo demás. Por comparación, un error en las cuotas manuales (F-02) afectaría a {{LINAJE:F-02}} cifras y uno en T-23 (cuotas de los escenarios) a {{LINAJE:T-23}}. El linaje es conservador: puede marcar como afectada una cifra que en realidad no cambie, pero no deja fuera ninguna que sí cambie.

## 6. Supuestos y limitaciones

- La pelea se supone el 15 de febrero de 2027 y el rival no está confirmado.
- La cuota de Pimblett procede de prensa (Heavy, 17 de octubre de 2026) que cita el agregador FightOdds.io, sin casa ni fecha conocidas.
- La probabilidad de mercado no tiene intervalo propio (D-33) y depende de una sola línea por escenario.
- El modelo no tiene en cuenta lesiones, campamento de entrenamiento ni categoría de peso (las dos peleas serían en peso ligero).
