// Free look for the real-time version of scene 1 (user's request 2026-11-27: "turn the head during the whole game").
// The Level Sequence drives the camera; this modifier turns the view on top of it, in the camera's own frame:
// mouse right/left = yaw within +-150 degrees, mouse up/down = pitch from -70 to +80, smoothed, no automatic return.
#pragma once

#include "CoreMinimal.h"
#include "Camera/CameraModifier.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameModeBase.h"
#include "OtlivLook.generated.h"

UCLASS()
class UOtlivLookModifier : public UCameraModifier
{
	GENERATED_BODY()
public:
	UOtlivLookModifier();
	virtual bool ModifyCamera(float DeltaTime, FMinimalViewInfo& InOutPOV) override;

	UPROPERTY(EditAnywhere, Category = "Look") float DegreesPerCount = 0.08f;
	UPROPERTY(EditAnywhere, Category = "Look") float YawLimit = 150.f;
	UPROPERTY(EditAnywhere, Category = "Look") float PitchDown = 70.f;
	UPROPERTY(EditAnywhere, Category = "Look") float PitchUp = 80.f;
	UPROPERTY(EditAnywhere, Category = "Look") float Smoothing = 12.f;     // 1/s: how fast the view follows the mouse

private:
	float TargetYaw = 0.f, TargetPitch = 0.f, Yaw = 0.f, Pitch = 0.f;
};

UCLASS()
class AOtlivPlayerController : public APlayerController
{
	GENERATED_BODY()
protected:
	virtual void BeginPlay() override;
};

UCLASS()
class AOtlivGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	AOtlivGameMode();
};
