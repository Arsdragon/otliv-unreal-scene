using UnrealBuildTool;

public class ScenesTarget : TargetRules
{
	public ScenesTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("Scenes");
	}
}
