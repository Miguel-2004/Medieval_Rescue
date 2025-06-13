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

    private struct WallKey
    {
        public int x;
        public int z;
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

    private enum WallDirection { Top = 0, Right = 1, Bottom = 2, Left = 3 }

    private readonly HashSet<WallKey> placedWalls = new();

    public static float CellSize => 2f;

    public static Vector3 GetTileWorldPosition(int gridX, int gridZ)
    {
        float worldX = gridX * CellSize + CellSize / 2f;
        float worldZ = (MapConditions.rows - 1 - gridZ) * CellSize + CellSize / 2f;
        return new Vector3(worldX, 0.5f, worldZ);
    }

    void Awake()
    {
        StaticCellSize = cellSize;
    }

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

    private void CollectPointsOfInterest(Dictionary<string, TileData> tiles)
    {
        foreach (var entry in tiles)
        {
            string[] coords = entry.Key.Split(',');
            int row = int.Parse(coords[0]);
            int col = int.Parse(coords[1]);
            int z = row - 1;
            int x = col - 1;
            var tile = entry.Value;

            if (tile.fireStatus > 0)
                fireList.Add(new Vector2Int(x, z));

            if (tile.hasPoi)
            {
                if (tile.numberVictims > 0)
                    victimList.Add(new Vector2Int(x, z));
                else
                    falseAlarmList.Add(new Vector2Int(x, z));
            }
        }
    }

    private void PlaceFloors(Dictionary<string, TileData> tiles)
    {
        foreach (var entry in tiles)
        {
            string[] coords = entry.Key.Split(',');
            int row = int.Parse(coords[0]);
            int col = int.Parse(coords[1]);
            int z = row - 1;
            int x = col - 1;

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
            string[] coords = entry.Key.Split(',');
            int row = int.Parse(coords[0]);
            int col = int.Parse(coords[1]);
            int z = row - 1;
            int x = col - 1;
            var tile = entry.Value;

            PlaceWallsForTile(tile, x, z, row, col);
        }
    }

    private bool ShouldSkipWalls(int row, int col)
    {
        return (row == 5 && col == 6);
    }

    private bool ShouldSwapLeftRight(int row, int col)
    {
        return
            (col == 1 && row >= 1 && row <= 6) ||
            (col == 8 && row >= 1 && row <= 4) ||
            (row == 6 && col == 6) ||
            (row == 1 && col == 3) || (row == 2 && col == 3) ||
            (row == 1 && col == 6) || (row == 2 && col == 6) ||
            (row == 6 && col == 5) || (row == 4 && col == 7) || (row == 3 && col == 7);
    }

    private bool ShouldMoveLeftToRight(int row, int col)
    {
        return
            (row == 3 && col == 2) || (row == 4 && col == 2) ||
            (row == 5 && col == 5) || (row == 6 && col == 5) ||
            (row == 5 && col == 7) || (row == 6 && col == 7) ||
            (row == 3 && col == 6) || (row == 4 && col == 6);
    }

    private bool ShouldForceRightToLeft(int row, int col)
    {
        return
            (row == 2 && col == 6) ||
            (row == 3 && col == 1) ||
            (row == 4 && col == 7) ||
            (row == 6 && col == 5);
    }

    private void PlaceWallsForTile(TileData tile, int x, int z, int row, int col)
    {
        if (ShouldSkipWalls(row, col))
            return;

        Vector3 center = GetTileWorldPosition(x, z);
        bool hasFF = tile.firefighters != null && tile.firefighters.Length > 0;

        if (tile.top > 0)
        {
            WallKey key = new WallKey(x, z, WallDirection.Top);
            if (!placedWalls.Contains(key))
            {
                Vector3 pos = center + new Vector3(0, 0, cellSize / 2);
                Quaternion rot = Quaternion.Euler(0, 0, 0);
                bool isOpen = tile.top == 2 && tile.isOpen && hasFF;
                PlaceWallObject(tile.top, tile.topHealth, isOpen, pos, rot, $"Wall_Top_{row}_{col}");
                placedWalls.Add(key);
            }
        }

        if (tile.right > 0)
        {
            WallKey key = new WallKey(x, z, WallDirection.Right);
            if (!placedWalls.Contains(key))
            {
                bool isOpen = tile.right == 2 && tile.isOpen && hasFF;
                Vector3 pos;
                Quaternion rot;

                if (ShouldSwapLeftRight(row, col) || ShouldForceRightToLeft(row, col))
                {
                    pos = center + new Vector3(-cellSize / 2, 0, 0);
                    rot = Quaternion.Euler(0, 270, 0);
                }
                else
                {
                    pos = center + new Vector3(cellSize / 2, 0, 0);
                    rot = Quaternion.Euler(0, 90, 0);
                }

                PlaceWallObject(tile.right, tile.rightHealth, isOpen, pos, rot, $"Wall_Right_{row}_{col}");
                placedWalls.Add(key);
            }
        }

        if (tile.bottom > 0)
        {
            WallKey key = new WallKey(x, z, WallDirection.Bottom);
            if (!placedWalls.Contains(key))
            {
                Vector3 pos = center + new Vector3(0, 0, -cellSize / 2);
                Quaternion rot = Quaternion.Euler(0, 180, 0);
                bool isOpen = tile.bottom == 2 && tile.isOpen && hasFF;
                PlaceWallObject(tile.bottom, tile.bottomHealth, isOpen, pos, rot, $"Wall_Bottom_{row}_{col}");
                placedWalls.Add(key);
            }
        }

        if (tile.left > 0)
        {
            WallKey key = new WallKey(x, z, WallDirection.Left);
            if (!placedWalls.Contains(key))
            {
                bool isOpen = tile.left == 2 && tile.isOpen && hasFF;
                Vector3 pos;
                Quaternion rot;

                if (ShouldSwapLeftRight(row, col) || ShouldMoveLeftToRight(row, col))
                {
                    pos = center + new Vector3(cellSize / 2, 0, 0);
                    rot = Quaternion.Euler(0, 90, 0);
                }
                else
                {
                    pos = center + new Vector3(-cellSize / 2, 0, 0);
                    rot = Quaternion.Euler(0, 270, 0);
                }

                PlaceWallObject(tile.left, tile.leftHealth, isOpen, pos, rot, $"Wall_Left_{row}_{col}");
                placedWalls.Add(key);
            }
        }
    }

    private void PlaceObjects()
    {
        foreach (var fire in fireList)
        {
            Vector3 pos = GetTileWorldPosition(fire.x, fire.y);
            GameObject instance = Instantiate(firePrefab, pos, Quaternion.identity, transform);
            instance.name = $"Fire_{fire.y + 1}_{fire.x + 1}";
            CenterObjectAtPosition(instance, pos);
        }

        foreach (var victim in victimList)
        {
            Vector3 pos = GetTileWorldPosition(victim.x, victim.y);
            pos.y = 0;
            GameObject instance = Instantiate(victimPrefab, pos, Quaternion.identity, transform);
            instance.name = $"Victim_{victim.y + 1}_{victim.x + 1}";
            CenterObjectAtPosition(instance, pos);
        }

        foreach (var falseAlarm in falseAlarmList)
        {
            Vector3 pos = GetTileWorldPosition(falseAlarm.x, falseAlarm.y);
            pos.y = 0;
            GameObject instance = Instantiate(victimPrefab, pos, Quaternion.identity, transform);
            instance.name = $"FalseAlarm_{falseAlarm.y + 1}_{falseAlarm.x + 1}";
            CenterObjectAtPosition(instance, pos);

            var renderer = instance.GetComponent<Renderer>();
            if (renderer != null)
                renderer.material.color = Color.yellow;
        }
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

        if (type == 1 && health <= 0)
        {
            var renderer = instance.GetComponent<Renderer>();
            if (renderer != null)
                renderer.material.color = Color.gray;
        }
    }

    private void CenterObjectAtPosition(GameObject obj, Vector3 target)
    {
        var rend = obj.GetComponent<Renderer>();
        if (rend != null)
        {
            Vector3 offset = rend.bounds.center - obj.transform.position;
            obj.transform.position = target - offset;
        }
    }

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
