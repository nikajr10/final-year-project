import { useRouter } from "expo-router";
import React, { useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { API_URL, FETCH_TIMEOUT_MS } from "../../constants/Config";

// 🚨 REPLACE WITH YOUR COMPUTER'S LOCAL IP ADDRESS
// Find it by running `ipconfig` (Windows) or `ipconfig getifaddr en0` (Mac)

export default function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password) {
      Alert.alert("Missing info", "Enter your email and password.");
      return;
    }

    setIsSubmitting(true);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.toLowerCase().trim(),
          password,
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);

      const data = await response.json();

      if (response.ok) {
        // ✅ Login Success
        console.log("✅ Login Successful:", data);

        await AsyncStorage.removeItem("session_greeting");
        await AsyncStorage.multiSet([
          ["access_token", data.access_token],
          ["user_name", data.name?.trim() || "User"],
        ]);

        // Navigate to Home
        router.replace("/(tabs)");
      } else {
        // ❌ Login Failed (Wrong password, etc.)
        Alert.alert("Login Failed", data.detail || "Invalid credentials.");
      }
    } catch (error) {
      console.error("❌ Network Error:", error);
      Alert.alert(
        "Connection Error",
        "Could not connect to the server. Check your Wi-Fi and IP address.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.select({ ios: "padding", android: undefined })}
    >
      <View className="flex-1 items-center justify-center bg-white px-4 dark:bg-zinc-950">
        <View className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
          <Text className="text-center text-lg font-semibold tracking-wide text-black-600 dark:text-zinc-400">
            Speech Enabled
          </Text>
          <Text className="mt-2 text-center text-3xl font-extrabold leading-9 text-[#007566] dark:text-[#007566]">
            Inventory Management{`\n`}System
          </Text>

          {/* Email Input */}
          <Text className="mt-8 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Email
          </Text>
          <TextInput
            value={email}
            onChangeText={setEmail}
            placeholder="e.g. admin@test.com"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          {/* Password Input */}
          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Password
          </Text>
          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="••••••"
            secureTextEntry
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          {/* Login Button */}
          <Pressable
            accessibilityRole="button"
            onPress={handleLogin}
            disabled={isSubmitting}
            className="mt-5 items-center rounded-xl bg-[#007566] py-3"
            style={({ pressed }) => [
              pressed && { opacity: 0.9 },
              isSubmitting && { opacity: 0.6 },
            ]}
          >
            <Text className="text-base font-bold text-white">
              {isSubmitting ? "Logging in..." : "Log in"}
            </Text>
          </Pressable>

          {/* Links */}
          <Pressable
            onPress={() => router.push("/(auth)/signup")}
            className="mt-3 items-center py-2"
          >
            <Text className="text-base font-semibold text-sky-700 dark:text-sky-400">
              Don’t have an account? Sign up
            </Text>
          </Pressable>

          <Pressable
            onPress={() => router.push("/(auth)/forgot-password")}
            className="items-center py-2"
          >
            <Text className="text-base font-semibold text-sky-700 dark:text-sky-400">
              Forgot password?
            </Text>
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

// import { useRouter } from "expo-router";
// import React, { useState } from "react";
// import {
//   Alert,
//   KeyboardAvoidingView,
//   Platform,
//   Pressable,
//   Text,
//   TextInput,
//   View,
// } from "react-native";
// import AsyncStorage from "@react-native-async-storage/async-storage";

// // ✅ MOCK LOGIN — No backend needed for UI development
// // Replace handleLogin with the real API version when backend is ready.
// // Any email + password will work.

// const MOCK_USER = {
//   access_token: "mock_token_for_ui_dev_12345",
//   name: "Dev User",
// };

// export default function LoginScreen() {
//   const router = useRouter();
//   const [email, setEmail] = useState("");
//   const [password, setPassword] = useState("");
//   const [isSubmitting, setIsSubmitting] = useState(false);

//   const handleLogin = async () => {
//     if (!email.trim() || !password) {
//       Alert.alert("Missing info", "Enter your email and password.");
//       return;
//     }

//     setIsSubmitting(true);

//     // Simulate a small network delay for realistic feel
//     await new Promise((resolve) => setTimeout(resolve, 800));

//     try {
//       // 🟡 MOCK: Save a fake token to AsyncStorage
//       await AsyncStorage.setItem("access_token", MOCK_USER.access_token);

//       Alert.alert("Welcome back!", "You have logged in successfully (mock).");

//       // Navigate to Home
//       router.replace("/(tabs)");
//     } catch (error) {
//       console.error("❌ Mock login error:", error);
//       Alert.alert("Error", "Something went wrong with mock login.");
//     } finally {
//       setIsSubmitting(false);
//     }
//   };

//   /* ─────────────────────────────────────────────────────────────
//      REAL LOGIN (uncomment + remove mock above when backend ready)
//   ─────────────────────────────────────────────────────────────
//   import { API_URL } from "../../constants/Config";

//   const handleLogin = async () => {
//     if (!email.trim() || !password) {
//       Alert.alert("Missing info", "Enter your email and password.");
//       return;
//     }
//     setIsSubmitting(true);
//     try {
//       const response = await fetch(`${API_URL}/api/auth/login`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({
//           email: email.toLowerCase().trim(),
//           password: password,
//         }),
//       });
//       const data = await response.json();
//       if (response.ok) {
//         await AsyncStorage.setItem("access_token", data.access_token);
//         Alert.alert("Welcome back!", "You have logged in successfully.");
//         router.replace("/(tabs)");
//       } else {
//         Alert.alert("Login Failed", data.detail || "Invalid credentials.");
//       }
//     } catch (error) {
//       Alert.alert("Connection Error", "Could not connect to the server.");
//     } finally {
//       setIsSubmitting(false);
//     }
//   };
//   ───────────────────────────────────────────────────────────── */

//   return (
//     <KeyboardAvoidingView
//       style={{ flex: 1 }}
//       behavior={Platform.select({ ios: "padding", android: undefined })}
//     >
//       <View className="flex-1 items-center justify-center bg-white px-4 dark:bg-zinc-950">
//         <View className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
//           <Text className="text-center text-lg font-semibold tracking-wide text-black-600 dark:text-zinc-400">
//             Speech Enabled
//           </Text>
//           <Text className="mt-2 text-center text-3xl font-extrabold leading-9 text-[#007566] dark:text-[#007566]">
//             Inventory Management{`\n`}System
//           </Text>

//           {/* 🟡 Mock mode indicator — remove before production */}
//           <View className="mt-3 rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-900/30">
//             <Text className="text-center text-xs font-medium text-amber-700 dark:text-amber-400">
//               🛠 Mock Mode — Any email & password will log you in
//             </Text>
//           </View>

//           {/* Email Input */}
//           <Text className="mt-8 text-sm font-semibold text-slate-600 dark:text-slate-300">
//             Email
//           </Text>
//           <TextInput
//             value={email}
//             onChangeText={setEmail}
//             placeholder="e.g. admin@test.com"
//             autoCapitalize="none"
//             autoCorrect={false}
//             keyboardType="email-address"
//             className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
//           />

//           {/* Password Input */}
//           <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">
//             Password
//           </Text>
//           <TextInput
//             value={password}
//             onChangeText={setPassword}
//             placeholder="••••••"
//             secureTextEntry
//             className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
//           />

//           {/* Login Button */}
//           <Pressable
//             accessibilityRole="button"
//             onPress={handleLogin}
//             disabled={isSubmitting}
//             className="mt-5 items-center rounded-xl bg-[#007566] py-3"
//             style={({ pressed }) => [
//               pressed && { opacity: 0.9 },
//               isSubmitting && { opacity: 0.6 },
//             ]}
//           >
//             <Text className="text-base font-bold text-white">
//               {isSubmitting ? "Logging in..." : "Log in"}
//             </Text>
//           </Pressable>

//           {/* Links */}
//           <Pressable
//             onPress={() => router.push("/(auth)/signup")}
//             className="mt-3 items-center py-2"
//           >
//             <Text className="text-base font-semibold text-sky-700 dark:text-sky-400">
//               Don't have an account? Sign up
//             </Text>
//           </Pressable>

//           <Pressable
//             onPress={() => router.push("/(auth)/forgot-password")}
//             className="items-center py-2"
//           >
//             <Text className="text-base font-semibold text-sky-700 dark:text-sky-400">
//               Forgot password?
//             </Text>
//           </Pressable>
//         </View>
//       </View>
//     </KeyboardAvoidingView>
//   );
// }
