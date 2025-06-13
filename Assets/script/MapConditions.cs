using UnityEngine;

public class MapConditions : MonoBehaviour
{
    // Daño general del entorno
    public static int damageCounter = 0;
    public static int maxDamage = 24;
    public static int explosionDamage = 2;

    // Salud máxima de estructuras
    public static int maxHealth = 4;

    // Dimensiones del mapa
    public static int rows = 6;
    public static int cols = 8;

    // Tamaño de cada celda
    public static float cellWidth = 10f;
    public static float cellHeight = 10f;
    public static float wallThickness = 0.5f;

    // Método para reiniciar el daño
    public static void Reset()
    {
        damageCounter = 0;
    }
}