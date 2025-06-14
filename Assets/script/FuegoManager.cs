using System.Collections.Generic;
using UnityEngine;

public class FuegoManager : MonoBehaviour
{
    [Header("Prefabs")]
    [SerializeField] private GameObject firePrefab;
    [SerializeField] private GameObject smokePrefab;

    // Guarda los efectos visuales activos en cada celda
    private Dictionary<Vector2Int, GameObject> fuegoInstanciado = new();

    /// <summary>
    /// Actualiza el estado de fuego/humo en la celda especificada.
    /// </summary>
    /// <param name="fireStatus">0 = limpio, 1 = humo, 2 = fuego</param>
    /// <param name="gridY">Fila (tile.y)</param>
    /// <param name="gridX">Columna (tile.x)</param>
    public void ActualizarFuego(int fireStatus, int gridY, int gridX)
    {
        Vector2Int key = new Vector2Int(gridX, gridY);

        // Eliminar visual previo si existe
        if (fuegoInstanciado.TryGetValue(key, out GameObject existente))
        {
            Destroy(existente);
            fuegoInstanciado.Remove(key);
        }

        // Decidir qué instanciar
        GameObject prefab = null;

        if (fireStatus == 1 && smokePrefab != null)
            prefab = smokePrefab;
        else if (fireStatus == 2 && firePrefab != null)
            prefab = firePrefab;

        if (prefab != null)
        {
            // Corregido: invertir la fila para alinear con la cuadrícula
            int z = MapConditions.rows - 1 - gridY;
            Vector3 posicion = TileBuilder.GetTileWorldPosition(gridX, z);
            posicion.y = 0;
            GameObject efecto = Instantiate(prefab, posicion, Quaternion.identity);
            fuegoInstanciado[key] = efecto;
            Debug.Log($"Instanciado {(fireStatus == 2 ? "FUEGO" : "HUMO")} en ({gridY},{gridX}) en posición {posicion}");
        }
        else
        {
            Debug.Log($"No se instanció nada en ({gridY},{gridX}), fireStatus={fireStatus}");
        }
    }

    /// <summary>
    /// Limpia todo el estado de fuego/humo del mapa.
    /// </summary>
    public void Reiniciar()
    {
        foreach (var obj in fuegoInstanciado.Values)
            Destroy(obj);

        fuegoInstanciado.Clear();
    }
}
