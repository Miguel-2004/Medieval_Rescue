using UnityEngine;

public class MapConditions : MonoBehaviour
{
    public static int damageCounter = 0;
    public static int maxDamage = 24;
    public static int explosionDamage = 2;
    public static int maxHealth = 4;

    public static int rows = 6;
    public static int cols = 8;

    public static float cellWidth = 10f;
    public static float cellHeight = 10f;
    public static float wallThickness = 0.5f;

    public static void Reset()
    {
        damageCounter = 0;
    }

    // NUEVO: método utilitario para calcular la posición centrada
    public static Vector3 GetWorldPosition(int x, int y)
    {
        float offsetX = cellWidth / 2f;
        float offsetZ = cellHeight / 2f;

        float worldX = x * cellWidth + offsetX;
        float worldZ = (rows - 1 - y) * cellHeight + offsetZ;

        return new Vector3(worldX, 0.5f, worldZ);
    }
}
