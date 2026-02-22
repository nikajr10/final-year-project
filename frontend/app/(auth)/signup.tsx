import { useRouter } from "expo-router";
import React, { useMemo, useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";

// ✅ USE THE SAME IP THAT WORKED FOR LOGIN
const API_URL = "http://192.168.1.95:8000";

export default function SignupScreen() {
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validationError = useMemo(() => {
    if (!fullName.trim()) return "Full name is required.";
    if (!email.trim()) return "Email is required.";
    if (!email.includes("@")) return "Enter a valid email.";
    if (password.length < 6) return "Password must be at least 6 characters.";
    if (confirmPassword !== password) return "Passwords do not match.";
    return null;
  }, [fullName, email, password, confirmPassword]);

  const handleSignup = async () => {
    if (validationError) {
      Alert.alert("Fix signup details", validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      console.log(`🔌 Attempting Signup to: ${API_URL}/auth/register`);

      const response = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: fullName,
          email: email.toLowerCase().trim(),
          password: password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // ✅ Signup Success
        console.log("✅ Signup Successful:", data);
        Alert.alert("Account created", "Signup successful. Please log in.");
        router.replace("/(auth)/login");
      } else {
        // ❌ Signup Failed
        Alert.alert("Signup failed", data.detail || "Something went wrong.");
      }
    } catch (error) {
      console.error("❌ Network Error:", error);
      Alert.alert("Connection Error", "Could not reach the server.");
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
          <Text className="text-center text-sm font-semibold tracking-wide text-zinc-600 dark:text-zinc-400">
            Speech Enabled
          </Text>
          <Text className="mt-2 text-center text-3xl font-extrabold leading-9 text-purple-700 dark:text-purple-300">
            Inventory Management{`\n`}System
          </Text>

          <Text className="mt-8 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Full Name
          </Text>
          <TextInput
            value={fullName}
            onChangeText={setFullName}
            placeholder="e.g. Ram Bahadur"
            autoCapitalize="words"
            autoCorrect={false}
            textContentType="name"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Email
          </Text>
          <TextInput
            value={email}
            onChangeText={setEmail}
            placeholder="e.g. ram@gmail.com"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            textContentType="emailAddress"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Password
          </Text>
          <TextInput
            value={password}
            onChangeText={setPassword}
            placeholder="••••••"
            secureTextEntry
            textContentType="newPassword"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          <Text className="mt-4 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Confirm Password
          </Text>
          <TextInput
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            placeholder="••••••"
            secureTextEntry
            textContentType="newPassword"
            className="mt-2 rounded-xl border border-slate-600 px-3 py-3 text-base text-zinc-900 dark:border-slate-500 dark:text-zinc-100"
          />

          <Pressable
            accessibilityRole="button"
            onPress={handleSignup}
            disabled={isSubmitting}
            className="mt-5 items-center rounded-xl bg-purple-700 py-3"
            style={({ pressed }) => [
              pressed && { opacity: 0.9 },
              isSubmitting && { opacity: 0.6 },
            ]}
          >
            <Text className="text-base font-bold text-white">
              {isSubmitting ? "Creating..." : "Sign up"}
            </Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            onPress={() => router.push("/(auth)/login")}
            className="mt-3 items-center py-2"
            style={({ pressed }) => [pressed && { opacity: 0.85 }]}
          >
            <Text className="text-base font-semibold text-sky-700 dark:text-sky-400">
              Already have an account? Log in
            </Text>
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}