# Fitness App React Native API Integration Guide

This guide shows how to connect an Expo React Native app to the Django DRF backend.

Base API URL:

```ts
const BASE_URL = "http://YOUR_COMPUTER_IP:8000/api";
```

For Android emulator you can often use:

```ts
const BASE_URL = "http://10.0.2.2:8000/api";
```

For iPhone/Android physical device, use your computer LAN IP:

```ts
const BASE_URL = "http://192.168.1.100:8000/api";
```

Do not use `localhost` on a physical phone because it points to the phone itself.

## 1. Install Required Package

```bash
npx expo install expo-secure-store
```

## 2. Axios API Instance

If you are using Axios, create one shared instance and use it everywhere.

Important local URL note:

```ts
// Include :8000 for Django runserver.
// Use your computer's real LAN IP, not 192.168.1.255.
baseURL: "http://192.168.1.100:8000/api"
```

`192.168.1.255` is usually a broadcast address, so it often will not work. Find your Mac IP and use that instead.

Create:

```text
utils/api.ts
```

```ts
import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import * as SecureStore from "expo-secure-store";

const api = axios.create({
  baseURL: "http://YOUR_COMPUTER_IP:8000/api",
  timeout: 120000,
});

export async function getAccessToken() {
  return SecureStore.getItemAsync("accessToken");
}

export async function getRefreshToken() {
  return SecureStore.getItemAsync("refreshToken");
}

export async function saveTokens(access: string, refresh: string) {
  await SecureStore.setItemAsync("accessToken", access);
  await SecureStore.setItemAsync("refreshToken", refresh);
}

export async function clearTokens() {
  await SecureStore.deleteItemAsync("accessToken");
  await SecureStore.deleteItemAsync("refreshToken");
}

async function refreshAccessToken() {
  const refresh = await getRefreshToken();
  if (!refresh) return null;

  try {
    const response = await axios.post(
      "http://YOUR_COMPUTER_IP:8000/api/auth/token/refresh/",
      { refresh },
      { timeout: 30000 }
    );

    const access = response.data?.access;
    if (!access) {
      await clearTokens();
      return null;
    }

    await SecureStore.setItemAsync("accessToken", access);
    return access;
  } catch {
    await clearTokens();
    return null;
  }
}

api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const access = await getAccessToken();
  if (access) {
    config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined;

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/login/") &&
      !originalRequest.url?.includes("/auth/register/") &&
      !originalRequest.url?.includes("/auth/verify-otp/") &&
      !originalRequest.url?.includes("/auth/token/refresh/")
    ) {
      originalRequest._retry = true;

      const newAccess = await refreshAccessToken();
      if (newAccess) {
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        return api(originalRequest);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

For screens, import this instance:

```ts
import api from "@/utils/api";
```

## 3. Signup With OTP

### Register

```ts
import api from "@/utils/api";

export async function registerUser(name: string, email: string, password: string) {
  const response = await api.post("/auth/register/", {
    name,
    email,
    password,
  });

  return response.data;
}
```

Response:

```json
{
  "success": true,
  "message": "OTP sent to your email.",
  "email": "user@example.com"
}
```

After this, navigate to your OTP screen and pass the email.

### Verify OTP

```ts
import api, { saveTokens } from "@/utils/api";

export async function verifySignupOtp(email: string, code: string) {
  const response = await api.post("/auth/verify-otp/", { email, code });
  const data = response.data;

  if (data?.tokens) {
    await saveTokens(data.tokens.access, data.tokens.refresh);
  }

  return data;
}
```

Response:

```json
{
  "success": true,
  "message": "Email verified successfully.",
  "tokens": {
    "access": "ACCESS_TOKEN",
    "refresh": "REFRESH_TOKEN"
  },
  "user": {
    "id": "uuid",
    "name": "John Doe",
    "email": "user@example.com",
    "profile_image": null
  }
}
```

## 4. Login

```ts
import api, { saveTokens } from "@/utils/api";

export async function loginUser(email: string, password: string) {
  const response = await api.post("/auth/login/", { email, password });
  const data = response.data;

  if (data?.tokens) {
    await saveTokens(data.tokens.access, data.tokens.refresh);
  }

  return data;
}
```

If email is not verified, backend returns:

```json
{
  "success": false,
  "message": "Email not verified. A new OTP has been sent.",
  "requires_verification": true,
  "email": "user@example.com"
}
```

In that case, navigate to OTP screen.

## 5. Logout

```ts
import api, { clearTokens, getRefreshToken } from "@/utils/api";

export async function logoutUser() {
  const refresh = await getRefreshToken();

  await api.post("/auth/logout/", { refresh });

  await clearTokens();
}
```

Important: logout requires an access token in the `Authorization` header. The `apiCall` helper adds it automatically.

## 6. Forgot Password

### Send Reset OTP

```ts
import api from "@/utils/api";

export async function forgotPassword(email: string) {
  const response = await api.post("/auth/forgot-password/", { email });
  return response.data;
}
```

Response:

```json
{
  "success": true,
  "message": "Password reset OTP sent to your email."
}
```

Navigate to reset password screen with the email.

### Reset Password

```ts
import api from "@/utils/api";

export async function resetPassword(
  email: string,
  code: string,
  newPassword: string
) {
  const response = await api.post("/auth/reset-password/", {
    email,
    code,
    new_password: newPassword,
  });

  return response.data;
}
```

Response:

```json
{
  "success": true,
  "message": "Password reset successfully."
}
```

After success, navigate to login screen.

## 7. Current User Profile

### Get Profile

```ts
import api from "@/utils/api";

export async function getProfile() {
  const response = await api.get("/users/me/");
  return response.data;
}
```

### Update Profile

```ts
import api from "@/utils/api";

export async function updateProfile(name: string, phone?: string, bio?: string) {
  const response = await api.put("/users/me/", { name, phone, bio });
  return response.data;
}
```

### Upload Avatar

```ts
import api from "@/utils/api";

export async function uploadAvatar(imageUri: string) {
  const formData = new FormData();

  formData.append("profile_image", {
    uri: imageUri,
    name: "avatar.jpg",
    type: "image/jpeg",
  } as any);

  const response = await api.put("/users/me/avatar/", formData);
  return response.data;
}
```

## 8. Exercises

### Get Paginated Exercise Feed

```ts
import api from "@/utils/api";

export async function getExercises({
  page = 1,
  pageSize = 10,
  search = "",
  category = "",
  difficulty = "",
} = {}) {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(pageSize));

  if (search) params.set("search", search);
  if (category) params.set("category", category);
  if (difficulty) params.set("difficulty", difficulty);

  const response = await api.get(`/exercises/?${params.toString()}`);
  return response.data;
}
```

Response:

```json
{
  "count": 25,
  "next": "http://localhost:8000/api/exercises/?page=2&page_size=10",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "title": "Push Ups",
      "category": "pushup",
      "difficulty": "Beginner",
      "duration": "10 mins",
      "media_type": "video",
      "image_url": null,
      "thumbnail_url": "http://localhost:8000/media/exercise_thumbnails/thumb.jpg",
      "trainer_name": "John Doe",
      "trainer_image": null,
      "is_bookmarked": false,
      "created_at": "2026-06-05T..."
    }
  ]
}
```

Use `thumbnail_url` in your feed cards.

Do not expect uploaded video URL in feed. Video URL is returned in detail API.

### Get Exercise Detail

```ts
import api from "@/utils/api";

export async function getExerciseDetail(id: string) {
  const response = await api.get(`/exercises/${id}/`);
  return response.data;
}
```

Detail response includes:

```json
{
  "id": "uuid",
  "title": "Push Ups",
  "description": "Workout description",
  "media_type": "video",
  "image_url": null,
  "thumbnail_url": "http://localhost:8000/media/exercise_thumbnails/thumb.jpg",
  "video_url": "http://localhost:8000/media/exercise_videos/video.mp4",
  "muscles": ["Chest", "Triceps"],
  "steps": ["Start in plank", "Lower body", "Push up"],
  "sets": "3 Sets",
  "reps": "12 Reps"
}
```

Use:

- `media_type === "image"`: show `image_url`
- `media_type === "video"`: show video player using `video_url`
- `thumbnail_url`: show poster/preview image

### Create Exercise With Image

```ts
import api from "@/utils/api";

type UploadProgressCallback = (progress: number) => void;

type CreateExerciseInput = {
  title: string;
  category: string;
  difficulty: "Beginner" | "Intermediate" | "Advanced";
  duration: string;
  description: string;
  muscles: string[];
  steps: string[];
  sets?: string;
  reps?: string;
  imageUri?: string;
};

export async function createExerciseWithImage(
  input: CreateExerciseInput,
  onProgress?: UploadProgressCallback
) {
  const formData = new FormData();

  formData.append("title", input.title);
  formData.append("category", input.category);
  formData.append("difficulty", input.difficulty);
  formData.append("duration", input.duration);
  formData.append("description", input.description);
  formData.append("muscles", JSON.stringify(input.muscles));
  formData.append("steps", JSON.stringify(input.steps));
  if (input.sets) formData.append("sets", input.sets);
  if (input.reps) formData.append("reps", input.reps);

  if (input.imageUri) {
    formData.append("image", {
      uri: input.imageUri,
      name: "exercise.jpg",
      type: "image/jpeg",
    } as any);
  }

  const response = await api.post("/exercises/", formData, {
    onUploadProgress: (event) => {
      if (!event.total || !onProgress) return;
      const progress = Math.round((event.loaded * 100) / event.total);
      onProgress(progress);
    },
  });

  return response.data;
}
```

### Create Exercise With Video

```ts
import api from "@/utils/api";

type UploadProgressCallback = (progress: number) => void;

type CreateVideoExerciseInput = {
  title: string;
  category: string;
  difficulty: "Beginner" | "Intermediate" | "Advanced";
  duration: string;
  description: string;
  muscles: string[];
  steps: string[];
  sets?: string;
  reps?: string;
  videoUri: string;
};

export async function createExerciseWithVideo(
  input: CreateVideoExerciseInput,
  onProgress?: UploadProgressCallback
) {
  const formData = new FormData();

  formData.append("title", input.title);
  formData.append("category", input.category);
  formData.append("difficulty", input.difficulty);
  formData.append("duration", input.duration);
  formData.append("description", input.description);
  formData.append("muscles", JSON.stringify(input.muscles));
  formData.append("steps", JSON.stringify(input.steps));
  if (input.sets) formData.append("sets", input.sets);
  if (input.reps) formData.append("reps", input.reps);

  formData.append("video", {
    uri: input.videoUri,
    name: "exercise.mp4",
    type: "video/mp4",
  } as any);

  const response = await api.post("/exercises/", formData, {
    onUploadProgress: (event) => {
      if (!event.total || !onProgress) return;
      const progress = Math.round((event.loaded * 100) / event.total);
      onProgress(progress);
    },
  });

  return response.data;
}
```

Important: send either `image` or `video`, not both.

### Update Exercise

```ts
import api from "@/utils/api";

type UploadProgressCallback = (progress: number) => void;

export async function updateExercise(
  id: string,
  formData: FormData,
  onProgress?: UploadProgressCallback
) {
  const response = await api.put(`/exercises/${id}/`, formData, {
    onUploadProgress: (event) => {
      if (!event.total || !onProgress) return;
      const progress = Math.round((event.loaded * 100) / event.total);
      onProgress(progress);
    },
  });

  return response.data;
}
```

### Upload Progress Usage Example

```tsx
import { useState } from "react";
import { createExerciseWithVideo } from "@/utils/exercises";

export function CreateWorkoutScreen() {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  async function handleSubmit() {
    try {
      setIsUploading(true);
      setUploadProgress(0);

      await createExerciseWithVideo(
        {
          title: "Push Up Demo",
          category: "pushup",
          difficulty: "Beginner",
          duration: "10 mins",
          description: "Demo workout video",
          muscles: ["Chest", "Triceps"],
          steps: ["Start in plank", "Lower body", "Push up"],
          sets: "3 Sets",
          reps: "12 Reps",
          videoUri: selectedVideoUri,
        },
        setUploadProgress
      );

      setUploadProgress(100);
    } finally {
      setIsUploading(false);
    }
  }

  return null;
}
```

Use `uploadProgress` to render your progress bar:

```tsx
<View style={{ height: 8, backgroundColor: "#e5e7eb", borderRadius: 999 }}>
  <View
    style={{
      height: 8,
      width: `${uploadProgress}%`,
      backgroundColor: "#0d9488",
      borderRadius: 999,
    }}
  />
</View>
```

Note: progress is measured while the phone uploads the file to Django. After upload reaches 100%, the backend may still need a short moment to save the file and generate the video thumbnail.

### Delete Exercise

```ts
import api from "@/utils/api";

export async function deleteExercise(id: string) {
  const response = await api.delete(`/exercises/${id}/`);
  return response.data;
}
```

### My Exercises

```ts
import api from "@/utils/api";

export async function getMyExercises() {
  const response = await api.get("/exercises/mine/");
  return response.data;
}
```

## 9. Bookmarks

### Toggle Bookmark

```ts
import api from "@/utils/api";

export async function toggleBookmark(exerciseId: string) {
  const response = await api.post(`/bookmarks/${exerciseId}/toggle/`);
  return response.data;
}
```

Response:

```json
{
  "success": true,
  "is_bookmarked": true,
  "message": "Exercise bookmarked."
}
```

### Get Saved Exercises

```ts
import api from "@/utils/api";

export async function getSavedExercises() {
  const response = await api.get("/bookmarks/");
  return response.data;
}
```

## 10. Recommended Screen Flow

Auth:

```text
SignUpScreen
  -> VerifyOtpScreen
  -> HomeScreen

LoginScreen
  -> HomeScreen

ForgotPasswordScreen
  -> ResetPasswordScreen
  -> LoginScreen
```

Exercise:

```text
HomeScreen
  -> ExerciseDetailScreen

CreateExerciseScreen
  -> HomeScreen or MyExercisesScreen

MyExercisesScreen
  -> EditExerciseScreen
```

## 11. Common 401 Problems

If API returns `401`, check:

```text
Authorization: Bearer ACCESS_TOKEN
```

Protected APIs:

```text
/users/me/
/users/me/avatar/
/exercises/
/exercises/{id}/
/exercises/mine/
/bookmarks/
/bookmarks/{exercise_id}/toggle/
/auth/logout/
```

Public APIs:

```text
/auth/register/
/auth/verify-otp/
/auth/resend-otp/
/auth/login/
/auth/forgot-password/
/auth/reset-password/
/auth/token/refresh/
```

## 12. Local vs Production Media URLs

Local development returns URLs like:

```text
http://localhost:8000/media/exercise_videos/video.mp4
```

Production with S3 returns URLs like:

```text
https://your-bucket.s3.amazonaws.com/exercise_videos/video.mp4
```

Your React Native app should use the URL returned by the API directly.

## 13. Swagger Docs

Backend Swagger:

```text
http://localhost:8000/api/docs/
```

Use Swagger to confirm request bodies and test APIs quickly.
