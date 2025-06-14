using System.Collections.Generic;
using UnityEngine;

public class TileBuilder : MonoBehaviour
{
    [Header("Prefabs")]
    [SerializeField] private GameObject wallPrefab;
    [SerializeField] private GameObject floorPrefab;
    [SerializeField] private GameObject firePrefab;
    [SerializeField] private GameObject victimPrefab;
    [SerializeField] private GameObject doorClosedPrefab;
    [SerializeField] private GameObject doorOpenPrefab;

    [Header("Configuración")]
    [SerializeField] private float cellSize = 2f;
    public static float StaticCellSize = 2f;

    [Header("Debug")]
    [SerializeField] private bool showDebugInfo = true;
    [SerializeField] private bool showCoordinateLabels = false;

    private int rows = MapConditions.rows;
    private int cols = MapConditions.cols;

    private readonly HashSet<Vector2Int> fireList = new();
    private readonly HashSet<Vector2Int> victimList = new();
    private readonly HashSet<Vector2Int> falseAlarmList = new();

    private enum WallDirection { Top = 0, Right = 1, Bottom = 2, Left = 3 }

    private struct WallKey
    {
        public int x, z;
        public WallDirection direction;

        public WallKey(int x, int z, WallDirection dir)
        {
            this.x = x;
            this.z = z;
            this.direction = dir;
        }

        public override bool Equals(object obj)
        {
            return obj is WallKey other &&
                   x == other.x && z == other.z && direction == other.direction;
        }

        public override int GetHashCode()
        {
            return (x * 1000 + z) * 10 + (int)direction;
        }
    }

    private readonly HashSet<WallKey> placedWalls = new();

    public static float CellSize => 2f;

    public static Vector3 GetTileWorldPosition(int gridX, int gridZ)
    {
        float worldX = gridX * CellSize + CellSize / 2f;
        float worldZ = (MapConditions.rows - 1 - gridZ) * CellSize + CellSize / 2f;
        return new Vector3(worldX, 0.5f, worldZ);
    }

    void Awake() => StaticCellSize = cellSize;

    public void GenerateFromTiles(Dictionary<string, TileData> tiles)
    {
        ClearScene();
        CollectPointsOfInterest(tiles);
        PlaceFloors(tiles);
        PlaceWalls(tiles);
        PlaceObjects();
    }

    private void ClearScene()
    {
        placedWalls.Clear();
        fireList.Clear();
        victimList.Clear();
        falseAlarmList.Clear();

        foreach (Transform child in transform)
            DestroyImmediate(child.gameObject);
    }

    private void ParseCoords(string key, out int row, out int col, out int x, out int z)
    {
        string[] coords = key.Split(',');
        row = int.Parse(coords[0]);
        col = int.Parse(coords[1]);
        z = row - 1;
        x = col - 1;
    }

    private void CollectPointsOfInterest(Dictionary<string, TileData> tiles)
    {
        foreach (var entry in tiles)
        {
            ParseCoords(entry.Key, out _, out _, out int x, out int z);
            var tile = entry.Value;

            if (tile.fireStatus > 0) fireList.Add(new Vector2Int(x, z));
            if (!tile.hasPoi) continue;

            if (tile.numberVictims > 0)
                victimList.Add(new Vector2Int(x, z));
            else
                falseAlarmList.Add(new Vector2Int(x, z));
        }
    }

    private void PlaceFloors(Dictionary<string, TileData> tiles)
    {
        foreach (var entry in tiles)
        {
            ParseCoords(entry.Key, out int row, out int col, out int x, out int z);
            Vector3 center = GetTileWorldPosition(x, z);
            GameObject floor = Instantiate(floorPrefab, center + Vector3.down * 0.5f, Quaternion.identity, transform);
            floor.name = $"Floor_{row}_{col}";
            CenterObjectAtPosition(floor, center + Vector3.down * 0.5f);
        }
    }

    private void PlaceWalls(Dictionary<string, TileData> tiles)
    {
        foreach (var entry in tiles)
        {
            ParseCoords(entry.Key, out int row, out int col, out int x, out int z);
            var tile = entry.Value;
            if (ShouldSkipWalls(row, col)) continue;

            bool hasFF = tile.firefighters != null && tile.firefighters.Length > 0;

            TryPlaceWall(tile, WallDirection.Top, row, col, x, z, tile.top, tile.topHealth, tile.top == 2 && tile.isOpen && hasFF);
            TryPlaceWall(tile, WallDirection.Right, row, col, x, z, tile.right, tile.rightHealth, tile.right == 2 && tile.isOpen && hasFF);
            TryPlaceWall(tile, WallDirection.Bottom, row, col, x, z, tile.bottom, tile.bottomHealth, tile.bottom == 2 && tile.isOpen && hasFF);
            TryPlaceWall(tile, WallDirection.Left, row, col, x, z, tile.left, tile.leftHealth, tile.left == 2 && tile.isOpen && hasFF);
        }
    }

    private void TryPlaceWall(TileData tile, WallDirection dir, int row, int col, int x, int z, int value, int health, bool isOpen)
    {
        WallKey key = new(x, z, dir);
        if (value <= 0 || placedWalls.Contains(key)) return;

        Vector3 center = GetTileWorldPosition(x, z);
        Vector3 offset = dir switch
        {
            WallDirection.Top => new Vector3(0, 0, cellSize / 2),
            WallDirection.Bottom => new Vector3(0, 0, -cellSize / 2),
            WallDirection.Left => new Vector3(-cellSize / 2, 0, 0),
            WallDirection.Right => new Vector3(cellSize / 2, 0, 0),
            _ => Vector3.zero
        };

        Quaternion rot = dir switch
        {
            WallDirection.Top => Quaternion.Euler(0, 0, 0),
            WallDirection.Bottom => Quaternion.Euler(0, 180, 0),
            WallDirection.Left => (ShouldSwapLeftRight(row, col) || ShouldMoveLeftToRight(row, col)) ? Quaternion.Euler(0, 90, 0) : Quaternion.Euler(0, 270, 0),
            WallDirection.Right => (ShouldSwapLeftRight(row, col) || ShouldForceRightToLeft(row, col)) ? Quaternion.Euler(0, 270, 0) : Quaternion.Euler(0, 90, 0),
            _ => Quaternion.identity
        };

        PlaceWallObject(value, health, isOpen, center + offset, rot, $"Wall_{dir}_{row}_{col}");
        placedWalls.Add(key);
    }

    private void PlaceObjects()
    {
        foreach (var fire in fireList)
            SpawnObject(firePrefab, fire, "Fire");

        foreach (var victim in victimList)
            SpawnObject(victimPrefab, victim, "Victim");

        foreach (var falseAlarm in falseAlarmList)
            SpawnObject(victimPrefab, falseAlarm, "FalseAlarm", Color.yellow);
    }

    private void SpawnObject(GameObject prefab, Vector2Int coords, string prefix, Color? color = null)
    {
        Vector3 pos = GetTileWorldPosition(coords.x, coords.y);
        pos.y = 0;
        GameObject instance = Instantiate(prefab, pos, Quaternion.identity, transform);
        instance.name = $"{prefix}_{coords.y + 1}_{coords.x + 1}";
        CenterObjectAtPosition(instance, pos);

        if (color.HasValue && instance.TryGetComponent(out Renderer rend))
            rend.material.color = color.Value;
    }

    private void PlaceWallObject(int type, int health, bool isOpen, Vector3 pos, Quaternion rot, string name)
    {
        GameObject prefab = type switch
        {
            1 => wallPrefab,
            2 => isOpen ? doorOpenPrefab : doorClosedPrefab,
            _ => null
        };

        if (prefab == null) return;

        pos.y = 0;
        GameObject instance = Instantiate(prefab, pos, rot, transform);
        instance.name = name;

        if (type == 1 && health <= 0 && instance.TryGetComponent(out Renderer rend))
            rend.material.color = Color.gray;
    }

    private void CenterObjectAtPosition(GameObject obj, Vector3 target)
    {
        if (obj.TryGetComponent(out Renderer rend))
        {
            Vector3 offset = rend.bounds.center - obj.transform.position;
            obj.transform.position = target - offset;
        }
    }

    private bool ShouldSkipWalls(int row, int col) => (row == 5 && col == 6);

    private bool ShouldSwapLeftRight(int row, int col) =>
        (col == 1 && row <= 6) || (col == 8 && row <= 4) ||
        (row == 6 && col == 6) || (row == 1 && col == 3) ||
        (row == 2 && col == 3) || (row == 1 && col == 6) ||
        (row == 2 && col == 6) || (row == 6 && col == 5) ||
        (row == 4 && col == 7) || (row == 3 && col == 7);

    private bool ShouldMoveLeftToRight(int row, int col) =>
        (row == 3 && col == 2) || (row == 4 && col == 2) ||
        (row == 5 && col == 5) || (row == 6 && col == 5) ||
        (row == 5 && col == 7) || (row == 6 && col == 7) ||
        (row == 3 && col == 6) || (row == 4 && col == 6);

    private bool ShouldForceRightToLeft(int row, int col) =>
        (row == 2 && col == 6) || (row == 3 && col == 1) ||
        (row == 4 && col == 7) || (row == 6 && col == 5);

    void OnDrawGizmos()
    {
        if (!showDebugInfo) return;
        Gizmos.color = Color.gray;

        for (int x = 0; x <= cols; x++)
            Gizmos.DrawLine(new Vector3(x * cellSize, 0.01f, 0), new Vector3(x * cellSize, 0.01f, rows * cellSize));

        for (int z = 0; z <= rows; z++)
            Gizmos.DrawLine(new Vector3(0, 0.01f, z * cellSize), new Vector3(cols * cellSize, 0.01f, z * cellSize));

#if UNITY_EDITOR
        if (showCoordinateLabels)
        {
            for (int x = 0; x < cols; x++)
                for (int z = 0; z < rows; z++)
                {
                    Vector3 pos = GetTileWorldPosition(x, z);
                    pos.y = 0.1f;
                    UnityEditor.Handles.Label(pos, $"[{z + 1},{x + 1}]");
                }
        }
#endif
    }
}
