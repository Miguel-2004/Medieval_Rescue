using UnityEngine;
using System.Collections;
using UnityEngine.Networking;
using System.Collections.Generic;
using Newtonsoft.Json; // INSTALADO DESDE EL PACKAGE MANAGER

public class MapaClient : MonoBehaviour
{
    string url = "http://localhost:8585";

    void Start()
    {
        Debug.Log("Iniciando solicitud al servidor...");
        StartCoroutine(SolicitarMapaInicial());
    }

    IEnumerator SolicitarMapaInicial()
    {
        UnityWebRequest www = UnityWebRequest.PostWwwForm(url, "");

        yield return www.SendWebRequest();

        if (www.result == UnityWebRequest.Result.Success)
        {
            string jsonTexto = www.downloadHandler.text;
            Debug.Log("Respuesta del servidor:\n" + jsonTexto);

            Dictionary<string, TileData> tiles = ProcesarJSON(jsonTexto);

            foreach (KeyValuePair<string, TileData> kvp in tiles)
            {
                Debug.Log($"Tile {kvp.Key}: FireStatus={kvp.Value.fireStatus}, POI={kvp.Value.hasPoi}");
            }
        }
        else
        {
            Debug.LogError("Error en POST: " + www.error);
        }
    }

    Dictionary<string, TileData> ProcesarJSON(string jsonTexto)
    {
        // Usamos Newtonsoft para el diccionario
        return JsonConvert.DeserializeObject<Dictionary<string, TileData>>(jsonTexto);
    }
}

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
