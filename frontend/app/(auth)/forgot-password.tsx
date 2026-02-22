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

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const [usernameOrEmail, setUsernameOrEmail] = useState("");

  const handleReset = async () => {
    if (!usernameOrEmail.trim()) {
      Alert.alert("Missing info", "Enter your username or email.");
      return;
    }

    // Placeholder until backend supports password reset.
    Alert.alert("Request received (demo)", "Password reset is not wired yet.");
    router.replace("/(auth)/login");
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.select({ ios: "padding", android: undefined })}
    >
      <View className="flex-1 items-center justify-center bg-white px-4 dark:bg-zinc-950">
        <View className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
          <Text className="text-center text-2xl font-extrabold text-zinc-900 dark:text-zinc-100">
            Reset password
          </Text>
          <Text className="mt-2 text-center text-base text-zinc-600 dark:text-zinc-400">
            Enter your username or email to request a reset.
          </Text>

          <Text className="mt-6 text-sm font-semibold text-slate-600 dark:text-slate-300">
            Username or email
          </Text>
          <TextInput
            value={usernameOrEmail}
            onChangeText={setUsernameOrEmail}
            placeholder="e.g. ram"
            autoCapitalize="none"
            autoCorrect={false}
            className="mt-2 rounded-xl border border-zinc-300 px-3 py-3 text-base text-zinc-900 dark:border-zinc-700 dark:text-zinc-100"
          />

          <Pressable
            accessibilityRole="button"
            onPress={handleReset}
            className="mt-5 items-center rounded-xl bg-sky-700 py-3"
            style={({ pressed }) => [pressed && { opacity: 0.9 }]}
          >
            <Text className="text-base font-bold text-white">
              Send reset link
            </Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            onPress={() => router.back()}
            className="mt-3 items-center py-2"
            style={({ pressed }) => [pressed && { opacity: 0.85 }]}
          >
            <Text className="text-base font-semibold text-sky-700 dark:text-sky-400">
              Back
            </Text>
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}
