// Dynamic Expo config so the API URL comes from the environment / build profile
// instead of a hardcoded LAN IP. Set EXPO_PUBLIC_API_URL when running, e.g.
//   EXPO_PUBLIC_API_URL=http://192.168.1.10:8000/api/v1 npx expo start
const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const CAMERA_PERMISSION = "Доступ к камере нужен, чтобы прикреплять фото «до/после» к задачам.";
const PHOTOS_PERMISSION = "Доступ к фото нужен, чтобы прикреплять изображения к задачам.";
const LOCATION_PERMISSION = "Доступ к геолокации нужен, чтобы привязывать задачи и отметку «на месте» к координатам.";
const MIC_PERMISSION = "Доступ к микрофону нужен для голосового ввода задач.";

module.exports = {
  expo: {
    name: "UOTP",
    slug: "uotp",
    scheme: "uotp",
    version: "0.1.0",
    orientation: "portrait",
    userInterfaceStyle: "automatic",
    ios: {
      supportsTablet: true,
      infoPlist: {
        NSCameraUsageDescription: CAMERA_PERMISSION,
        NSPhotoLibraryUsageDescription: PHOTOS_PERMISSION,
        NSLocationWhenInUseUsageDescription: LOCATION_PERMISSION,
        NSMicrophoneUsageDescription: MIC_PERMISSION
      }
    },
    android: {
      permissions: ["CAMERA", "ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION", "RECORD_AUDIO"]
    },
    plugins: [
      "expo-router",
      "expo-secure-store",
      "expo-notifications",
      ["expo-image-picker", { cameraPermission: CAMERA_PERMISSION, photosPermission: PHOTOS_PERMISSION }],
      ["expo-location", { locationWhenInUsePermission: LOCATION_PERMISSION }],
      ["expo-audio", { microphonePermission: MIC_PERMISSION }]
    ],
    extra: {
      apiUrl: API_URL
    }
  }
};
