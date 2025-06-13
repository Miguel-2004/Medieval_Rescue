using UnityEngine;
using System.Collections;
using UnityEngine.Networking;
using System.Collections.Generic;
using Newtonsoft.Json;

public class MapaClient : MonoBehaviour
{
    string baseUrl = "http://localhost:8585";

    void Start()
    {
        Debug.Log("Enviando POST al servidor...");
        StartCoroutine(SolicitarMapaInicial());
    }

    IEnumerator SolicitarMapaInicial()
    {
        UnityWebRequest www = UnityWebRequest.PostWwwForm(baseUrl, "");
        yield return www.SendWebRequest();

        if (www.result == UnityWebRequest.Result.Success)
        {
            string jsonTexto = www.downloadHandler.text;
            Debug.Log("JSON recibido:\n" + jsonTexto);

            Dictionary<string, TileData> tiles = JsonConvert.DeserializeObject<Dictionary<string, TileData>>(jsonTexto);

            TileBuilder builder = FindAnyObjectByType<TileBuilder>();
            if (builder != null)
            {
                builder.GenerateFromTiles(tiles);
            }
            else
            {
                Debug.LogError("No se encontró un objeto con TileBuilder en la escena.");
            }

            // Inicia la segunda petición
            StartCoroutine(SolicitarMovimientos());
        }
        else
        {
            Debug.LogError("Error en POST: " + www.error);
        }
    }

    IEnumerator SolicitarMovimientos()
    {
        string movimientosUrl = baseUrl + "/movimientos";
        UnityWebRequest www = UnityWebRequest.PostWwwForm(movimientosUrl, "");
        yield return www.SendWebRequest();

        if (www.result == UnityWebRequest.Result.Success)
        {
            string jsonTexto = www.downloadHandler.text;
            Debug.Log("JSON recibido (Movimientos):\n" + jsonTexto);

            Dictionary<string, List<BotMovimiento>> movimientos = JsonConvert.DeserializeObject<Dictionary<string, List<BotMovimiento>>>(jsonTexto);

            MovimientoManager mm = FindAnyObjectByType<MovimientoManager>();
            if (mm != null)
                mm.ProcesarMovimientos(movimientos);
            else
                Debug.LogWarning("MovimientoManager no encontrado en la escena.");
        }
        else
        {
            Debug.LogError("Error al solicitar movimientos: " + www.error);
        }
    }
}

// ---------- DATA STRUCTURES ----------
[System.Serializable]
public class TileData
{
    public int top;
    public int left;
    public int bottom;
    public int right;
    public bool isOpen;
    public int topHealth;
    public int leftHealth;
    public int bottomHealth;
    public int rightHealth;
    public int fireStatus;
    public bool hasPoi;
    public int numberVictims;
    public string[] firefighters;
}

[System.Serializable]
public class BotMovimiento
{
    public int bot_id;
    public List<AgentStepDataWrapper> agent_step_data;
}

[System.Serializable]
public class AgentStepDataWrapper
{
    public int model_step_id;
    public AffectedTile affected_tiles_data;
}

[System.Serializable]
public class AffectedTile
{
    public int x, y;
    public int top, left, bottom, right;
    public bool isOpen;
    public int topHealth, leftHealth, bottomHealth, rightHealth;
    public int fireStatus;
    public bool hasPOI;
    public int numberOfVictims;
    public List<int> firefightersIDs;
    public string actions;
    public int dx, dy;
}
