# Registro de decisiones

Cada decisión de criterio del caso CD-726-017 queda registrada con su identificador, fecha, decisión y justificación. Las decisiones marcadas como PENDIENTE requieren verificación antes de usarse en cifras del informe.

## D-01 — Fecha de la pelea Topuria–Gaethje

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Decisión:** se adopta **2026-06-14** como fecha de la pelea Topuria–Gaethje (UFC Freedom 250).
- **Justificación:** es el valor de `event_date` que publica ufcstats.com y que recoge el dataset F-01 (`raw/UFC_full_data_silver_v2.csv`). Otras fuentes indican el 15 de junio por la diferencia horaria. Regla general: la fecha oficial de un evento es la de `event_date` de ufcstats (hora local del evento).

## D-02 — Identificación de peleadores

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Decisión:** los peleadores se identifican por su URL de ufcstats (`f_1_url`, `f_2_url`), no por su nombre.
- **Justificación:** el nombre no es una clave única: existe Aleksandre Topuria (hermano de Ilia) y al menos un nombre del dataset corresponde a dos peleadores distintos. La URL de ufcstats es estable y única por peleador.

## D-03 — Exclusión de las estadísticas `f_*_fighter_*` como predictores

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Decisión:** las columnas `f_*_fighter_*` no se usarán como predictores; las estadísticas de carrera se recalcularán a la fecha de cada pelea, usando solo peleas anteriores.
- **Justificación:** esas columnas son una instantánea actual del perfil del peleador (snapshot) e incluyen información posterior a cada pelea. Usarlas introduciría fuga temporal (*data leakage*) y sobreestimaría la capacidad predictiva del modelo.

## D-04 — Peleas sin ganador: empates y sin resultado

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-24 por jorgebb01. Verificación de las 3 peleas sin tarjetas completada el 2026-10-24 (F-08).
- **Decisión:** las 157 peleas de F-01 con `winner` vacío se clasifican según `result`:
  - **Empate (63):** `result` empieza por "Decision" (39 Majority, 17 Split, 7 Unanimous).
  - **Sin resultado (94):** `Overturned` (59), `Could Not Continue` (33) y `Other` (2). No cuentan como victoria ni derrota.
  - **Uso en el modelo:** empates y sin resultado se excluyen de la variable objetivo (gana/pierde), pero se conservan en el historial de cada peleador (récord, actividad, peleas previas).
- **Justificación:** se revisaron las tarjetas de `result_details` de las 63 decisiones: 60 son empates según las tarjetas (p. ej. dos jueces 28-28 en un empate mayoritario). F-04 (archangel0x01) clasifica como `draw` las 32 de ellas posteriores a 2018, lo que confirma el criterio con una fuente independiente. Las otras 94 no tienen ganador porque el resultado se anuló o la pelea no pudo terminar, que equivale a sin resultado (NC).
- **Verificación de las 3 decisiones sin tarjetas en F-01:** Brad Gumm vs CJ Fernandes (UFC 27, 2000-09-22, `c078544a32e18ba3`), Tim Lajcik vs Ron Waterman (UFC 22, 1999-09-24, `96c247ba0eb1ac65`) y Jens Pulver vs Alfonso Alcarez (UFC 22, 1999-09-24, `a1c1e3c1e9c6cf1e`). Las tres son **empates** según ufcstats (página de la pelea y fichas de ambos peleadores, vía Wayback Machine, D-13), Wikipedia (revisión fija) y Sherdog: 15 de 15 registros coinciden (M-0157 a M-0171, F-08). En Pulver vs Alcarez se anunció primero una victoria de Pulver que después se cambió a empate; vale el resultado oficial final de ufcstats. Las discrepancias menores entre fuentes (categoría de peso en Gumm vs Fernandes, árbitro en Pulver vs Alcarez) no afectan a `winner`; se toma ufcstats como referencia. Las tarjetas de estas 3 peleas no están publicadas en ninguna de las fuentes consultadas.
- **Regla:** un `winner` vacío con `result` de decisión es **empate** cuando las tarjetas de `result_details` dan empate o cuando hay verificación manual en F-08.

## D-05 — Procedencia de F-01 y fecha de descarga

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-24 por jorgebb01: `fecha_consulta` de F-01 = **2026-10-22**.
- **Decisión:** F-01 procede de Kaggle `scarekrow/ufc-data`, **versión 21** (https://www.kaggle.com/datasets/scarekrow/ufc-data/versions/21, publicada el 2026-10-19 00:51 UTC con la nota "Update 2026-10-18: UFC Fight Night: Buckley vs. Malott (13 new fights, 8,950 total)"). Como `fecha_consulta` se propone la fecha real de descarga, que solo puede confirmar el responsable. Debe estar entre el 2026-10-19 y el 2026-10-24, porque la versión 22 (8.964 peleas) se publicó el 2026-10-24 a las 22:56 UTC. El archivo de `raw/` tiene fecha de modificación 2026-10-22 02:44 UTC, que es un indicio pero no una prueba. La URL debe citar la versión 21, no la página genérica, porque la versión actual ya es distinta.
- **Justificación:** se descargó la versión 21 en un directorio temporal y el SHA-256 del CSV coincide exactamente con el de F-01 (7bdfb1b9…3f67), igual que el tamaño (11.314.591 bytes). La licencia es "Other (specified in description)" y la descripción no detalla condiciones de uso, así que conviene revisarla antes de redistribuir.

## D-06 — Rankings de F-01 tratados como instantánea, no como ranking en la fecha de la pelea

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-24 por jorgebb01. No se incorpora por ahora un histórico de rankings: la cuota de cierre ya refleja el nivel de cada peleador en la fecha de la pelea. Se reconsiderará solo si el modelo necesita el ranking como variable.
- **Decisión:** `f_1_ranking` y `f_2_ranking` no se usarán como ranking histórico ni como predictor, por el mismo motivo que D-03. Si se necesita el ranking en una fecha concreta, se tomará de una fuente histórica, que habrá que registrar.
- **Justificación:** la descripción del dataset en Kaggle dice: "Current UFC rankings are a snapshot as of scrape time only, not historical rankings at the time of each fight". En F-01 el valor es constante en todas las peleas de cada peleador: Gaethje 0, Topuria 1 y Pimblett 6, desde 2017 hasta 2026. Como candidata para el ranking histórico queda `jerzyszocik/ufc-rankings-history` (Kaggle, CC0, actualizado el 2026-10-22), que no se ha descargado ni evaluado.

## D-07 — Fuente, casa y momento de la cuota

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-24 por jorgebb01, con el punto (b) concretado tras la ingesta de D-12.
- **Decisión:** (a) la cuota de referencia para el modelo es la **de cierre**, la última antes de la pelea, porque es la que incorpora más información. La de apertura se conserva solo como descriptiva. (b) Orden de fuentes: 1) F-05 (archangel0x01, cierre por casa); 2) F-07 (jerzyszocik), última instantánea por casa antes de la fecha de la pelea, cuando F-05 no tenga la pelea (p. ej. UFC 298); 3) `manual/cuotas.csv` (F-02) para lo que no cubran ninguno de los dos. Siempre se excluyen los mercados de D-11, y la probabilidad de la pelea es la media entre casas de la probabilidad sin margen (D-08). (c) Cuando solo existe el "Closing range" agregado de BestFightOdds, que muestra dos extremos sin casa identificada, la probabilidad de cada extremo se calcula por separado y se usa el promedio. (d) Las filas `previa_no_cierre` (Covers, UFC 282) se usan solo si no hay ninguna otra cuota de esa pelea, marcadas como aproximación.
- **Justificación:** BFO no identifica la casa en su ficha de peleador y da un rango, no un único valor de cierre. Hay que elegir un criterio explícito en lugar de tomar un extremo en silencio.
- **Datasets de Kaggle evaluados (F-04/F-05 y F-07 incorporados por D-12; valihameed descartado):** `archangel0x01/ufc-fight-results-and-betting-props` (MIT, cierre por casa en formato americano y decimal, 2021–2026, coincide con BFO en UFC Freedom 250); `jerzyszocik/ufc-betting-odds-daily-dataset` (CC0, instantáneas diarias por casa con `fight_url` de ufcstats para unos 75.000 de 216.452 registros); `valihameed/ufc-stats` (MIT, cierre `RedOdds`/`BlueOdds`, pero vacío para Mitchell, Oliveira y Gaethje 2026).

## D-08 — Conversión de cuotas americanas a decimales y a probabilidad implícita

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-24 por jorgebb01.
- **Decisión:** `valor_decimal` = 1 + A/100 si A > 0, y 1 + 100/|A| si A < 0, redondeado a 4 decimales. Las comas de miles del original ("+1,200") se eliminan antes de convertir. Probabilidad implícita bruta = 1/decimal. Para eliminar el margen de la casa en un mercado de dos resultados, cada probabilidad se divide entre la suma de ambas (normalización proporcional).
- **Justificación:** son conversiones estándar. `valor_original` conserva siempre el texto de la fuente, sin las flechas de movimiento ▲▼ de BFO.

## D-09 — Discrepancia sobre la cuota de Topuria vs Gaethje ("6 a 1" del caso frente al cierre)

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-24 por jorgebb01.
- **Hechos:** el caso dice "favorito 6 a 1" y calcula la probabilidad como 6/7 ≈ 0,857, lo que equivale a Topuria -600 o decimal 1,167. En BestFightOdds, la apertura es Topuria -500 / Gaethje +385 (M-0043, M-0046). El cierre por casa en la página del evento está entre -450 y -500 para Topuria y entre +350 y +360 para Gaethje (M-0123 a M-0134), lo que da una probabilidad bruta de Topuria de entre 0,82 y 0,83. Además, la ficha de peleador de BFO muestra un "Closing range" de -500 a -250 para Topuria y de +210 a +360 para Gaethje (M-0044, M-0045, M-0047, M-0048). Los extremos -250 y +210 no corresponden a ninguna columna visible de la página del evento.
- **Decisión:** (a) el "6 a 1" se cita como dato del caso, sin fuente primaria localizada. Parece corresponder a líneas intermedias de mayo de 2026, no al cierre; F-07 (jerzyszocik, incorporado por D-12) lo confirma: entre abril y mayo de 2026 varias casas daban Topuria 1,12–1,13 y Gaethje 5,25–6,5 en decimal (p. ej. Nordic Bet el 2026-05-02: 1,12 / 6,5), y en junio las líneas se acercaron (Topuria 1,17–1,20). (b) Para esta pelea, el modelo usa el cierre por casa de la página del evento (excluyendo los mercados de predicción, D-11) y no el rango de la ficha de peleador.

## D-10 — Atribución errónea en BestFightOdds de UFC 298

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-24 por jorgebb01.
- **Decisión:** las cuotas de UFC 298 (Volkanovski vs. Topuria, 2024-02-17) que BFO publica bajo el perfil "Alexsandre Topuria" (`/fighters/alexsandre-topuria-15779`) se asignan a Ilia Topuria mediante `fight_url` y `fighter_url` de ufcstats (D-02) (M-0049 a M-0054).
- **Justificación:** UFC 298 tuvo como estelar a Volkanovski vs. Ilia Topuria, la pelea figura en F-01 con el `fighter_url` de Ilia y no aparece en la ficha BFO de Ilia (`ilia-topuria-8322`). Unir por nombre habría perdido la pelea o la habría asignado a otro peleador.
- **Recomendación (2026-10-24):** aprobar. F-07 (jerzyszocik) confirma la atribución de forma independiente de BFO: tiene la pelea con `fight_url` `bec3154a11df3299` y `fighter_url` de Ilia Topuria (`54f64b5e283b0ce7`), igual que F-01, con Volkanovski 1,70 / Topuria 2,20. Esos valores caen dentro del rango de cierre de BFO (Topuria -105…+128, Volkanovski -152…-120). F-05 no tiene cuotas de esta pelea (`has_odds` = False). Por D-07, la cuota de referencia de UFC 298 será la de F-07, y M-0049 a M-0054 quedan como verificación cruzada.

## D-11 — Exclusión de mercados de predicción e intercambio como cuota de cierre

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-24 por jorgebb01, ampliada a los datasets de Kaggle.
- **Decisión:** no se usan como cuota de cierre los mercados de predicción ni de intercambio entre apostadores:
  - BFO (`manual/cuotas.csv`): las columnas Kalshi y Polymarket se registran (M-0121, M-0122, M-0128, M-0129), pero no se usan.
  - F-05 (`raw/archangel0x01_v3/odds.csv`): se filtran las filas con `bookmaker` = `Kalshi` o `Polymarket`.
  - F-07 (`raw/jerzyszocik_v273/UFC_betting_odds.csv`): se filtran las filas con `source` = `Betfair` (intercambio); se conserva `Betfair Sportsbook`.
- **Justificación:** no son casas de apuestas, y su último precio puede reflejar negociación durante la pelea o después. En UFC Freedom 250, Kalshi muestra a Topuria +228 y a Gaethje -277, es decir, invertido respecto al resto del mercado, lo que es coherente con un precio tomado durante el combate que Gaethje ganó.

## D-12 — Incorporación de datasets de cuotas de Kaggle

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-24 por jorgebb01.
- **Decisión:** se incorporan a `raw/` dos datasets de cuotas, citados por versión fija: `archangel0x01/ufc-fight-results-and-betting-props` **v3** (F-04, F-05, F-06; MIT) y `jerzyszocik/ufc-betting-odds-daily-dataset` **v273** (F-07; CC0). Se guardan solo los CSV; los `.parquet` del archivo de archangel0x01 se descartan porque duplican el contenido. Se descarta `valihameed/ufc-stats` porque no tiene cuotas de Mitchell, Oliveira ni Gaethje 2026.
- **Justificación:** F-01 tiene las columnas de cuotas vacías. archangel0x01 aporta la cuota de cierre por casa, incluida Topuria vs Gaethje (coincide con la página del evento en BestFightOdds, F-02). jerzyszocik aporta `fight_url` de ufcstats para unir con F-01 sin depender de nombres (D-02) y las líneas futuras de la revancha. Ambos datasets se actualizan a menudo, por eso se cita la versión y no la página genérica. Las cuotas manuales de F-02 quedan como verificación cruzada y para los casos que no cubren estos datasets (p. ej. UFC 282).

## D-13 — Copias de Wayback Machine cuando ufcstats.com no se puede leer

- **Fecha:** 2026-10-24
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-24 por jorgebb01, con las dos condiciones de la recomendación.
- **Decisión:** cuando ufcstats.com no se puede leer en directo, se aceptan como fuente de nivel 1 las copias de Wayback Machine de sus páginas, descargadas sin modificar (sufijo `id_`). En `url` se registra la URL de la copia y en `notas`, la URL canónica de ufcstats.
- **Justificación:** el 2026-10-24 ufcstats.com devolvía un desafío JavaScript anti-bot por HTTP y rechazaba la conexión por HTTPS (evidencia en `manual/capturas/ufcstats_live_challenge_fight_c078544a32e18ba3.html`). No se intentó saltar ese control. Las copias de Wayback tienen fecha fija y no cambian, lo que facilita que el auditor las reproduzca.
- **Recomendación (2026-10-24):** aprobar, con dos condiciones: (1) preferir siempre la copia de Wayback más reciente anterior a la fecha de consulta y guardar su captura en `manual/capturas/` con hash; (2) si una cifra del informe depende de una página de ufcstats que solo se ha leído en Wayback, contrastarla con F-01 (que procede del mismo ufcstats) o con una segunda fuente (Sherdog, Wikipedia con revisión fija). Wayback es la única forma reproducible de citar ufcstats mientras esté bloqueado, y la URL de la copia no cambia, a diferencia de la página en directo.

## D-14 — Unión de F-04/F-05 con F-01 por fecha y nombres

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** F-04 se une con F-01 por fecha con tolerancia de ±2 días y nombres normalizados; se acepta una coincidencia con nombres solo compatibles cuando el candidato es único. Las peleas sin unión inequívoca quedan sin cuota de F-05 y se reportan.
- **Justificación:** F-04 no trae URL de ufcstats (D-02). En 311 peleas F-04 tiene la fecha 1–2 días después que F-01, por los husos horarios de eventos en Asia y Oceanía. Resultado de T-12: 4.472 de 4.477 unidas, ninguna ambigua; las 5 sin unir son alias (Cris Cyborg = Cristiane Justino, Jose Henrique = Jose Souza, Jo Sungbin = Sung Bin Jo) y solo una tiene cuotas (fight_id 4230). Si se necesitara, una tabla de alias en `manual/` con su fuente resolvería esos casos. Cuando F-04 y F-01 discrepan en el resultado (3 casos, anulados en F-01), prevalece F-01.

## D-15 — Historial: peleas del mismo día y cálculo de la racha

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** En las variables históricas, las peleas del mismo día (torneos de 1993–1999) no se ven entre sí. Para la racha, dentro de un mismo día las victorias cuentan antes, y un empate o un sin resultado ponen la racha a 0.
- **Justificación:** Las variables históricas solo pueden usar peleas estrictamente anteriores (D-03); en los torneos no hay un orden fiable dentro del día. La regla de la racha es una convención explícita para que el cálculo sea reproducible.

## D-16 — Duración de asalto de 5 minutos

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01. Nota: el supuesto es incorrecto para parte de las peleas de los primeros años de la UFC (sin asaltos o con asaltos de otra duración); no afecta al modelo si se entrena con peleas desde 2021 (D-18).
- **Decisión:** `duracion_seg` y las tasas por minuto se calculan con asaltos de 5 minutos para todas las épocas: (asalto final − 1) × 300 + reloj del asalto final.
- **Justificación:** F-01 no informa de la duración de los asaltos de cada época. Es el formato vigente en la UFC.

## D-17 — Exclusión de Matchbook en F-07

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** Se excluyen de F-07 las filas con `source` = `Matchbook` (959 filas).
- **Justificación:** Matchbook es un intercambio entre apostadores; se aplica el mismo criterio que D-11.

## D-18 — Cuotas de F-07: instantáneas previas y carga histórica `zewnetrzne`

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01, con condiciones.
- **Decisión:** (a) De F-07 solo se usan instantáneas tomadas el día UTC anterior a la pelea o antes (`adding_date` < `event_date`). (b) Se acepta como cuota de cierre histórica la carga `source` = `zewnetrzne` (capturada el 2025-07-27, posterior a las peleas, de una sola casa no identificada). Condiciones: (1) el dataset analítico lleva una columna que identifica las cuotas que proceden de esa carga; (2) el modelo se entrena con peleas desde 2021, donde F-05 cubre el 96,7 % de las cuotas; (3) el informe incluye un análisis de sensibilidad de la probabilidad de Topuria con y sin las 3 peleas suyas que dependen de esta carga (Zalal, Jackson y Volkanovski).
- **Justificación:** Es la única fuente de cierre para la mayoría de las peleas anteriores a 2021 (4.413 de las 4.417 peleas con cuota de F-07). No hay fuga temporal: son cuotas de cierre, publicadas antes de la pelea aunque se capturaran después. El riesgo es que la casa no está identificada, de ahí la marca y el análisis de sensibilidad. D-10 ya la acepta para UFC 298.

## D-19 — Rango de cierre de BestFightOdds

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** Cuando F-02 solo tiene el "Closing range" de BFO, se promedian las probabilidades brutas de los dos extremos de cada peleador y después se normaliza para quitar el margen (D-08).
- **Justificación:** Concreta el punto (c) de D-07 y garantiza que las dos probabilidades de la pelea sumen 1.

## D-20 — Casa repetida en la misma pelea de F-05

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** Si una casa aparece dos veces en la misma pelea de F-05, primero se promedian sus filas y después se hace la media entre casas.
- **Justificación:** Evita que una casa pese el doble. Caso detectado: fight_id 3085, BetWay, Chookagian con dos grafías del nombre.

## D-21 — Emparejamiento de las cuotas previas de Covers (UFC 282)

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** Las dos filas `previa_no_cierre` de Covers para Topuria vs Mitchell se emparejan por la URL del artículo, aunque cada lado indique una casa distinta ("DraftKings" / "no indicada en la fuente"). El resultado se marca como aproximación (D-07 d).
- **Justificación:** Es la única cuota disponible para esa pelea (F-05 y F-07 no la tienen).

## D-22 — Descarte de filas de F-07 con URL y nombre contradictorios

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** Se descartan las filas de F-07 en las que el nombre del peleador contradice su URL de ufcstats dentro de la misma pelea (17.870 filas usables, eventos del 2025-08-02 al 2025-09-06). No se reorientan por nombre.
- **Justificación:** Si se orientaran por URL la probabilidad saldría invertida (diferencias de hasta 0,66 con F-05). Reorientarlas por nombre sería suponer cuál de los dos campos es el correcto. Tras el descarte, la diferencia media con F-05 en las 1.671 peleas comunes es 0,011.

## D-23 — Edad, altura y alcance como excepción a D-03

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01, con la condición de que la edad se calcule a la fecha de cada pelea.
- **Decisión:** Se admiten como variables la fecha de nacimiento (para calcular la edad a la fecha de cada pelea), la altura y el alcance de `f_*_fighter_*`, aunque D-03 excluye el resto de esas columnas.
- **Justificación:** Son atributos que no dependen de peleas posteriores (la altura y el alcance de un adulto no cambian de forma relevante), así que no introducen fuga temporal. La edad calculada a la fecha de la pelea sí cambia con el tiempo y por eso no se usa la edad actual.

## D-24 — Fecha de las filas automáticas de la bitácora

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** En las filas T-07 en adelante de `bitacora.csv`, que escribe el pipeline, la columna `fecha` es la fecha de la última ejecución del pipeline, no la fecha en que se diseñó la transformación. Las filas T-00 a T-06 son manuales y conservan su fecha.
- **Justificación:** El pipeline regenera esas filas en cada ejecución (idempotencia); la fecha de ejecución indica cuándo se produjeron las salidas que hay en disco, que es lo que el auditor comprueba con `final/manifiesto_salidas.csv`.

## D-25 — Atributos físicos con valores distintos para un mismo peleador

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** cuando F-01 da más de un valor de fecha de nacimiento, altura o alcance para el mismo peleador (identificado por su URL de ufcstats, D-02), se usa un único valor por peleador: el de la fila de su pelea más reciente en F-01. Los peleadores afectados y los valores descartados se registran en la bitácora de la transformación que aplica la regla.
- **Justificación:** son atributos estáticos (D-23) y deberían ser únicos por peleador; la fila más reciente es la última actualización de ufcstats recogida en F-01. Casos detectados: 3 peleadores con fecha de nacimiento distinta, 3 con altura y 7 con alcance (p. ej. Wang Cong, Jose Delgado, Eric Nolan). Ninguno es Topuria, Gaethje ni Pimblett.

## D-26 — Datos ausentes en el modelo

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** En el modelo, las diferencias peleador − rival que no se pueden calcular valen 0, y la ausencia se recoge en 4 indicadores antisimétricos: `d_debut`, `d_sin_edad`, `d_sin_alcance` y `d_sin_estadisticas`. No se imputa ningún valor en el dataset analítico.
- **Justificación:** Un 0 en una diferencia antisimétrica no favorece a ninguno de los dos peleadores, y los indicadores permiten al modelo distinguir "sin dato" de "igualdad". Mantener el dataset sin imputar conserva la trazabilidad de cada valor hasta F-01.

## D-27 — Periodos de entrenamiento y regla de elección del modelo

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** Ajuste con peleas de 2021 a 2023, validación con 2024 para elegir la regularización C en una rejilla, y test con peleas del 2025-01-01 al 2026-10-17 (una fila por pelea). Gana el modelo con menor log-loss en test, pero un modelo propio solo sustituye al mercado si el IC95 de su diferencia de log-loss con el mercado queda entero por debajo de 0.
- **Justificación:** Validación temporal sin barajar, para no usar información futura (D-18 condición 2). La regla exige que un modelo propio mejore al mercado de forma estadísticamente clara antes de preferirlo. Resultado: se elige el mercado (C-043).

## D-28 — Fecha supuesta de la próxima pelea y fecha de corte del mercado

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** Los escenarios se calculan para una pelea el **2027-02-15** (supuesto) y solo usan información de mercado capturada hasta el **2026-10-25**.
- **Justificación:** El caso indica que el regreso se prevé para febrero de 2027 sin fecha confirmada. La fecha afecta a la edad y a los días de inactividad de los escenarios. El corte del mercado fija qué líneas se usan para que el resultado sea reproducible.

## D-29 — Intervalos de incertidumbre

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** Los intervalos de los modelos B y C en los escenarios se calculan con 300 réplicas bootstrap por peleas (semilla 726018); los intervalos de las métricas, con 1.000 réplicas pareadas (semilla 726017). El intervalo del mercado es el mínimo y el máximo de las líneas disponibles, y es de un solo punto cuando solo hay una línea.
- **Justificación:** El bootstrap por peleas recoge la incertidumbre del ajuste sin supuestos de distribución; las semillas fijas hacen los resultados reproducibles.

## D-30 — Identificación por nombres de las líneas futuras

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** Las líneas futuras de F-07 no tienen URL de ufcstats, así que se identifican por los dos nombres normalizados, como excepción a D-02. Solo se usan las capturadas entre el 2026-06-14 y el corte de D-28. Para Topuria–Pimblett solo se usa la línea de F-02 (M-0115 a M-0120), marcada como anterior a la derrota ante Gaethje.
- **Justificación:** Una pelea futura todavía no tiene página en ufcstats. El riesgo de confusión es bajo porque se exigen los dos nombres a la vez (Ilia Topuria con su rival, no Aleksandre Topuria). Limitación: la probabilidad de mercado del escenario Pimblett procede de una línea anterior a la derrota y probablemente está inflada.

## D-31 — Cuota vigente del escenario Topuria–Pimblett

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** la cuota de mercado del escenario Topuria–Pimblett es **Topuria -500 / Pimblett +375** (M-0172, M-0173), publicada por Heavy el 2026-10-17 citando el agregador FightOdds.io; `tipo_cuota` = `vigente_citada_prensa`. La línea de diciembre de 2025 (M-0115 a M-0120, -770/+510) se conserva solo como análisis de sensibilidad. Con D-08, la probabilidad de Topuria sin margen es ≈ 0,798.
- **Justificación:** es la única línea Topuria–Pimblett localizada posterior a la derrota ante Gaethje (2026-06-14); la anterior no refleja esa información. Es una excepción a la jerarquía de fuentes (prensa que cita a un agregador), por lo que se declaran como limitaciones: no se conoce la casa de apuestas ni la fecha en que FightOdds.io publicó la línea, y la página del agregador no se pudo leer (se cargaba con JavaScript y el acceso a su API quedó bloqueado). Búsquedas sin resultado en BFO, F-07, Covers, Action Network y DKNetwork, detalladas en el informe del investigador web.

## D-32 — Numeración de las entradas manuales de la bitácora

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** las entradas manuales de `bitacora.csv` posteriores a la creación del pipeline (ingestas y archivo de datos hechas a mano) se numeran con una serie propia: **I-01, I-02…**. T-00 a T-06 conservan su numeración. La serie T-07 en adelante queda reservada a las transformaciones que escribe el pipeline (D-24), que debe conservar intactas las filas T-00 a T-06 y todas las I-xx.
- **Justificación:** el pipeline regenera sus filas T-07+ en cada ejecución; una entrada manual con un ID de esa serie se sobrescribiría, y renumerar rompería las referencias de `final/cifras.csv` y `final/linaje.csv`.

## D-33 — Incertidumbre de la probabilidad de mercado

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** la probabilidad de mercado de cada escenario se presenta como **estimación puntual sin intervalo**, porque cada escenario tiene una sola línea vigente. El informe lo declara explícitamente y da como referencia de incertidumbre el IC95 bootstrap del modelo combinado C (D-29). No se construye una banda de calibración del mercado.
- **Justificación:** el modelo C empata con el mercado en test (D-27) y su intervalo recoge la incertidumbre del ajuste con un método ya aprobado; una banda de calibración añadiría un criterio nuevo difícil de justificar con una sola línea por escenario.

## D-34 — Elección de la cifra al azar en el simulacro de auditoría

- **Fecha:** 2026-10-25
- **Responsable:** jorgebb01
- **Estado:** APROBADA el 2026-10-25 por jorgebb01.
- **Decisión:** el botón "Cifra al azar" de la app (`/cifra-al-azar`) elige entre todas las cifras de `final/cifras.csv` con un generador no reproducible (`random.SystemRandom`), para que nadie pueda prever qué cifra saldrá. Con el parámetro opcional `?semilla=n` la elección es reproducible, para repetir un simulacro concreto si el profesor lo pide.
- **Justificación:** el simulacro exige que la cifra la elija el profesor sin que el equipo la conozca de antemano. La semilla opcional permite reconstruir después qué cifra se auditó. No afecta a ninguna cifra del informe.
