using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Material;
using CUE4Parse.UE4.Assets.Exports.StaticMesh;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Objects.Meshes;
using CUE4Parse.UE4.Versions;
using CUE4Parse.Utils;
using Newtonsoft.Json;
using System.Diagnostics;

// Annoying fucks.
#pragma warning disable CS8602 // Dereference of a possibly null reference.
#pragma warning disable CS8625 // Cannot convert null literal to non-nullable reference type.

// Functions

void log(object t)
{
    Console.WriteLine(t);
}

// this is bad but cba to do it properly with the code after it
var converters = new Dictionary<Type, JsonConverter>()
{
    { typeof(FColorVertexBuffer), new FColorVertexBufferCustomConverter() }
};
var settings = new JsonSerializerSettings { ContractResolver = new CustomResolver(converters) };

void writeToJSON(string path, string fileName, object data)
{
    var json = JsonConvert.SerializeObject(data, Formatting.Indented, settings);
    try
    {
        File.WriteAllText(Path.Combine(path, $"{fileName}.json"), json);
        #if (DEBUG)
        log($"Exported : {path}\\{fileName}");
        #endif
    }
    catch (Exception e)
    {
        log(e);
    }
}


string aesKey = "0x4BE71AF2459CF83899EC9DC2CB60E22AC4B3047E0211034BBABE9D174C069DD6";

#if DEBUG
string _gameDirectory = @"D:\Games\Riot Games\VALORANT\live\ShooterGame\Content\Paks";
string _exportPath = @"D:\_assets_\valorant";
string _objectPath = "ShooterGame/Content/Maps/Pitt/Pitt_Art_ASite";
#else
string _gameDirectory = args[0];
string _exportPath = args[1];
string _objectPath = args[2];
#endif


var stopwatch = new Stopwatch();
stopwatch.Start();

string objectsFolder = Path.Combine(_exportPath, "objects");
string overrideMaterialsFolder = Path.Combine(_exportPath, "materials_ovr");
string materialsFolder = Path.Combine(_exportPath, "materials");
string parentMaterialsFolder = Path.Combine(_exportPath, "parent_materials");
string umapsFolder = Path.Combine(_exportPath, "umaps");
string umapName = _objectPath.Split('/').Last();

var versions = new VersionContainer(EGame.GAME_Valorant);
var provider = new DefaultFileProvider(_gameDirectory, SearchOption.TopDirectoryOnly, false, versions);

provider.Initialize();
provider.SubmitKey(new FGuid(), new FAesKey(aesKey));
provider.LoadMappings();
provider.LoadLocalization(ELanguage.English);

var mapObjects = provider.LoadObjectExports(_objectPath);
var filterTypes = new List<string>() { "StaticMeshComponent", "InstancedStaticMeshComponent", "HierarchicalInstancedStaticMeshComponent", "PointLightComponent", "RectLightcomponent", "SpotLightComponent" };
var objectList = new List<UObject>();


// Create folders
var folders = new List<string>() { objectsFolder, overrideMaterialsFolder, materialsFolder, umapsFolder, parentMaterialsFolder };
foreach (string folder in folders)
{
    if (!Directory.Exists(folder))
    {
        Directory.CreateDirectory(folder);
    }
}



foreach (UObject mapObject in mapObjects)
{

    if (filterTypes.Any(mapObject.ExportType.Contains))
    {
        

        // Override Materials
        var om = mapObject.GetOrDefault<UObject[]>("OverrideMaterials", null);
        
        if (om != null)
        {
            foreach (var mat in om.Where(mat => mat != null))
            {
                var pm = mat.GetOrDefault<UUnrealMaterial>("Parent", null); ;

                if (pm != null)
                {
                    writeToJSON(parentMaterialsFolder, pm.Name, pm);
                }

                writeToJSON(overrideMaterialsFolder, mat.Name, mat);
            }
        }

        // Object
        var sm = mapObject.GetOrDefault<UStaticMesh>("StaticMesh", null);
        if (sm != null)
        {
            objectList.Add(mapObject);

            writeToJSON(objectsFolder, sm.Name, sm);

            // Static Materials
            var sm_materials = sm.StaticMaterials;
            if (sm_materials != null)
            {
                foreach (var mat in sm_materials.Where(mat => mat.MaterialInterface != null))
                {
                    var _mat = mat.MaterialInterface.Load();

                    if (_mat != null)
                    {
                        writeToJSON(materialsFolder, _mat.Name, _mat);

                        var pm = _mat.GetOrDefault<UUnrealMaterial>("Parent", null);

                        if (pm != null)
                        {
                            writeToJSON(parentMaterialsFolder, pm.Name, pm);
                        }
                    }
                }
            }
        }
    }


}

writeToJSON(umapsFolder, umapName, objectList);

// Just in case
//writeToJSON(umapsFolder, $"{umapName}_unfiltered", mapObjects);

stopwatch.Stop();
TimeSpan ts = stopwatch.Elapsed;
log($"Exported | {umapName} in {stopwatch.ElapsedMilliseconds} ms");

class FColorVertexBufferCustomConverter : JsonConverter<FColorVertexBuffer>
{
    public override void WriteJson(JsonWriter writer, FColorVertexBuffer value, JsonSerializer serializer)
    {
        writer.WriteStartObject();

        writer.WritePropertyName("Data");
        // serializer.Serialize(writer, value.Data); // saving space and time by only writing as hex
        writer.WriteStartArray();
        foreach (var c in value.Data)
            writer.WriteValue(UnsafePrint.BytesToHex(c.R, c.G, c.B, c.A)); // we need alpha even if it's 1 or 0...
        writer.WriteEndArray();

        writer.WritePropertyName("Stride");
        writer.WriteValue(value.Stride);

        writer.WritePropertyName("NumVertices");
        writer.WriteValue(value.NumVertices);

        writer.WriteEndObject();
    }

    public override FColorVertexBuffer ReadJson(JsonReader reader, Type objectType, FColorVertexBuffer existingValue, bool hasExistingValue,
        JsonSerializer serializer)
    {
        throw new NotImplementedException();
    }
}