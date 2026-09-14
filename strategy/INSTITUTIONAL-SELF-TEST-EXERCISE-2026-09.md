# Institutional Self-Test Exercise Plan — ciclo 2026-09

**Estado:** plan de ejercicio fechado. No acredita ejecucion ni cambia por si mismo ningun predicado de `strategy/INSTITUTIONAL-SELF-TEST.md`.

## Proposito

Diseñar una primera prueba operativa del self-test institucional contra cambios reales del repositorio, preservando exactamente la taxonomia y los ocho predicados del documento canonico. Cada fila solo puede terminar en `PASS`, `FAIL` o `NOT_DEMONSTRATED`, y solo con evidencia fechada del funcionamiento en el alcance declarado.

Este ejercicio no produce una puntuacion agregada ni convierte un numero de filas aprobadas en certificacion institucional. El release owner debe decidir por separado como afecta cada resultado al release.

## Alcance del ejercicio

El caso de prueba es la incorporacion de tres agentes de dominio —nowcasting convectivo, litigio laboral y localizacion ES/EN— junto con los controles de lint, revision y release que los rodean. Las anomalias utilizadas deben ser reversibles y no deben llegar a `main` como defectos deliberados.

Para cada predicado se registraran: alcance, evidencia fechada, resultado, reviewer, gap no resuelto, owner responsable y siguiente trigger de revision.

| # | Predicado canonico | Mecanismo de prueba previsto | Evidencia requerida para `PASS` | Estado inicial |
|---|---|---|---|---|
| 1 | Una advertencia critica llega a alguien que puede pausar o aceptar el riesgo | Introducir en una rama de prueba una anomalia material claramente identificable y comprobar si el canal de revision la eleva a un receptor humano con autoridad antes del merge | Referencia fechada a la advertencia, receptor autorizado, plazo y respuesta/decision | NOT_DEMONSTRATED |
| 2 | La sintesis permite reconstruir incertidumbre, supuestos, alternativas y confianza | Comparar una salida fuente tipada con el resumen usado para revision y verificar que los estados epistemicos sobreviven | Pares fuente/resumen fechados y revision que confirme o rechace la reconstruccion | NOT_DEMONSTRATED |
| 3 | El analisis independiente y la alternativa fuerte aparecen antes de decidir | Obtener una revision adversarial previa a la decision de merge sin instruir al reviewer sobre la conclusion deseada | Analisis previo fechado, alternativa material y evidencia de que existia capacidad real de objecion antes de decidir | NOT_DEMONSTRATED |
| 4 | Una objecion y su respuesta quedan registradas con responsable del riesgo residual | Conservar una objecion material en el registro de decision aunque el cambio sea finalmente aceptado | Objecion, evidencia citada, respuesta, identidad del decisor y aceptacion/rechazo del riesgo residual | NOT_DEMONSTRATED |
| 5 | Salir del rango validado exige autorizacion expresa conforme a criterios de parada predefinidos | Fijar antes de la prueba una condicion de parada y observar que la continuidad no ocurre por silencio cuando se alcanza | Criterio fechado anterior al incidente y decision expresa al alcanzarlo | NOT_DEMONSTRATED |
| 6 | La repeticion de una anomalia dispara revision del modelo/proceso, no otra excepcion aislada | Registrar dos ocurrencias comparables y comprobar si la segunda activa una revision acumulativa | Historial de ambas ocurrencias y cambio/revision del mecanismo causal o del control | NOT_DEMONSTRATED |
| 7 | Mejorar una metrica no sustituye el resultado superior declarado | Contrastar un resultado tecnico verde —por ejemplo, PR mergeable o CI parcial— con evidencia de que el objetivo operativo sigue preservado | Registro que incluya resultado, dano potencial y chequeo de gaming; no basta el estado de CI | NOT_DEMONSTRATED |
| 8 | La evaluacion compara el resultado con una prediccion fechada previa | Formular antes del ejercicio una expectativa verificable y revisarla despues contra lo ocurrido sin reescribirla retrospectivamente | Prediccion fechada, criterio de verificacion y comparacion posterior en el mismo alcance | NOT_DEMONSTRATED |

## Prediccion fechada del ejercicio

**Prediccion previa:** antes del 2026-10-15 se habra intentado ejecutar al menos una prueba completa de los predicados 1, 2, 3, 4, 5, 7 y 8 sobre un cambio real o fixture controlado del repositorio; el predicado 6 solo puede evaluarse si existen al menos dos anomalias comparables. Esta prediccion es evidencia potencial para la fila 8, no un criterio de certificacion agregado.

**Criterio de verificacion:** el registro posterior debe enumerar que filas fueron realmente ejercitadas, que evidencia fechada existe y por que cada fila recibe `PASS`, `FAIL` o permanece `NOT_DEMONSTRATED`.

## Condiciones de parada y seguridad

- No introducir defectos deliberados en `main`.
- No simular una segunda autoridad humana ni presentar un agente/modelo diferente como independencia institucional.
- Si no existe un receptor humano con autoridad real para una prueba, la fila correspondiente permanece `NOT_DEMONSTRATED`; el gap se documenta y se escala como limitacion de gobernanza.
- Un fallo tecnico de CI puede ser evidencia para una fila, pero CI no certifica por si solo funcionamiento institucional.
- No sumar filas, porcentajes ni umbrales de aprobacion globales.

## Registro de ejecucion

Cuando se ejecute el ejercicio, añadir una tabla fechada separada con: `scope`, `evidence`, `date`, `result`, `reviewer`, `unresolved_gap`, `accountable_owner` y `next_review_trigger`. Hasta entonces este archivo sigue siendo un plan de ejercicio, no un execution log.
