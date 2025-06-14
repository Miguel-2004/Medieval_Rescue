using UnityEngine;
using System.Collections;
using System.Collections.Generic;

public class MovimientoManager : MonoBehaviour
{
    [Header("Prefabs")]
    public GameObject firefighterPrefab;

    private Dictionary<int, GameObject> bomberosInstanciados = new();

    public float pasoDelay = 1f; // segundos entre pasos

    public void ProcesarMovimientos(Dictionary<string, List<BotMovimiento>> movimientos)
    {

        List<BotMovimiento> botsOrdenados = new();

        foreach (var run in movimientos)
        {
            botsOrdenados.AddRange(run.Value);
        }


        StartCoroutine(EjecutarPorBot(botsOrdenados));
    }

    IEnumerator EjecutarPorBot(List<BotMovimiento> bots)
    {
        foreach (var bot in bots)
        {
            int botId = bot.bot_id;
            List<AgentStepDataWrapper> pasos = bot.agent_step_data;

            if (pasos.Count == 0) continue;

            // Instanciar bombero si no existe
            if (!bomberosInstanciados.ContainsKey(botId))
            {
                var inicio = pasos[0].affected_tiles_data;
                Vector3 posInicial = TileBuilder.GetTileWorldPosition(inicio.y, inicio.x);
                GameObject bombero = Instantiate(firefighterPrefab, posInicial, Quaternion.identity);
                bombero.name = $"Bombero_{botId}";
                bomberosInstanciados[botId] = bombero;
            }

            GameObject agente = bomberosInstanciados[botId];

            foreach (var paso in pasos)
            {
                var tile = paso.affected_tiles_data;
                Vector3 destino = TileBuilder.GetTileWorldPosition(tile.y, tile.x);
                Vector3 origen = agente.transform.position;

                float t = 0f;
                while (t < pasoDelay)
                {
                    t += Time.deltaTime;
                    float factor = Mathf.Clamp01(t / pasoDelay);
                    agente.transform.position = Vector3.Lerp(origen, destino, factor);
                    yield return null;
                }

                agente.transform.position = destino;
                Debug.Log($"Bot {botId} ejecutó paso {paso.model_step_id}");
            }

            yield return new WaitForSeconds(0.2f); // pausa opcional entre bots
        }

        Debug.Log("Todos los bots han ejecutado sus rutas.");
    }
}
