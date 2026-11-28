#include "OtlivLook.h"
#include "Camera/PlayerCameraManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

UOtlivLookModifier::UOtlivLookModifier()
{
	Priority = 200;          // after everything else: the look is the last turn of the view
	AlphaInTime = 0.f;
	AlphaOutTime = 0.f;
	// for checks without a mouse:  Scenes.exe -LookYaw=60 -LookPitch=10 ; sensitivity:  -LookSens=0.08
	FParse::Value(FCommandLine::Get(), TEXT("LookYaw="), TargetYaw);
	FParse::Value(FCommandLine::Get(), TEXT("LookPitch="), TargetPitch);
	FParse::Value(FCommandLine::Get(), TEXT("LookSens="), DegreesPerCount);
	Yaw = TargetYaw;
	Pitch = TargetPitch;
}

bool UOtlivLookModifier::ModifyCamera(float DeltaTime, FMinimalViewInfo& InOutPOV)
{
	if (const APlayerController* PC = CameraOwner ? CameraOwner->GetOwningPlayerController() : nullptr)
	{
		float DX = 0.f, DY = 0.f;
		PC->GetInputMouseDelta(DX, DY);
		TargetYaw = FMath::Clamp(TargetYaw + DX * DegreesPerCount, -YawLimit, YawLimit);
		TargetPitch = FMath::Clamp(TargetPitch + DY * DegreesPerCount, -PitchDown, PitchUp);
	}
	Yaw = FMath::FInterpTo(Yaw, TargetYaw, DeltaTime, Smoothing);
	Pitch = FMath::FInterpTo(Pitch, TargetPitch, DeltaTime, Smoothing);
	// in the camera's own frame: yaw around its up axis, then pitch around its new right axis
	const FQuat Look = FQuat(FVector::UpVector, FMath::DegreesToRadians(Yaw)) * FQuat(FVector::RightVector, FMath::DegreesToRadians(-Pitch));
	InOutPOV.Rotation = (InOutPOV.Rotation.Quaternion() * Look).Rotator();
	return false;
}

void AOtlivPlayerController::BeginPlay()
{
	Super::BeginPlay();
	bShowMouseCursor = false;
	SetInputMode(FInputModeGameOnly());
	if (PlayerCameraManager)
	{
		PlayerCameraManager->AddNewCameraModifier(UOtlivLookModifier::StaticClass());
	}
}

AOtlivGameMode::AOtlivGameMode()
{
	PlayerControllerClass = AOtlivPlayerController::StaticClass();
}
