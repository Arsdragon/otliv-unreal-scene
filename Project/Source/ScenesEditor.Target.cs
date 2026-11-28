using UnrealBuildTool;

public class ScenesEditorTarget : TargetRules
{
	public ScenesEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("Scenes");
	}
}
