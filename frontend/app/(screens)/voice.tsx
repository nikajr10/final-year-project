import { router, Stack } from "expo-router";
import { Image } from "expo-image";
import { ArrowLeft } from "lucide-react-native";
import React, { useState, useEffect, useRef } from "react";
import {
  Platform,
  Pressable,
  Text,
  View,
  ActivityIndicator,
  Alert,
  SafeAreaView,
  StatusBar,
} from "react-native";
import { Audio } from "expo-av";
import { API_URL } from "../../constants/Config";
import { getApiErrorMessage, readApiResponse } from "../../utils/apiResponse";

const Mic = require("../../assets/images/green_mic.svg");

type Decision = {
  action: string;
  item: string;
  item_nepali: string;
  qty_changed: number;
  new_stock: number;
  unit: string;
  alert_message: string | null;
};

const VOICE_TIMEOUT_MS = 180000;

export default function Voice() {
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState("Hold the Button...");
  const [decision, setDecision] = useState<Decision | null>(null);
  const [transcription, setTranscription] = useState(
    "Ask about stock or sales",
  );

  const uploadInFlight = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const formatDecisionQuantity = (nextDecision: Decision) => {
    const normalizedAction = nextDecision.action.toLowerCase();
    const absoluteQuantity = Math.abs(Number(nextDecision.qty_changed ?? 0));
    const quantityText = `${absoluteQuantity} ${nextDecision.unit}`.trim();

    if (normalizedAction.includes("add")) {
      return `Added ${quantityText}`;
    }

    if (
      normalizedAction.includes("remove") ||
      normalizedAction.includes("deduct") ||
      normalizedAction.includes("sale")
    ) {
      return `Deducted ${quantityText}`;
    }

    if (absoluteQuantity === 0) {
      return "No stock change";
    }

    return `${nextDecision.qty_changed > 0 ? "+" : "-"}${quantityText}`;
  };

  // ── Permissions ────────────────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== "granted")
        Alert.alert("Permission missing", "Please allow microphone access.");
    })();
    return () => {
      if (recording) recording.stopAndUnloadAsync().catch(() => {});
    };
  }, []);

  // ── Recording options ──────────────────────────────────────────────────────
  const recordingOptions: Audio.RecordingOptions = {
    android: {
      extension: ".wav",
      outputFormat: Audio.AndroidOutputFormat.MPEG_4,
      audioEncoder: Audio.AndroidAudioEncoder.AAC,
      sampleRate: 44100,
      numberOfChannels: 2,
      bitRate: 128000,
    },
    ios: {
      extension: ".wav",
      audioQuality: Audio.IOSAudioQuality.HIGH,
      sampleRate: 44100,
      numberOfChannels: 1,
      bitRate: 128000,
      linearPCMBitDepth: 16,
      linearPCMIsBigEndian: false,
      linearPCMIsFloat: false,
    },
    web: { mimeType: "audio/wav", bitsPerSecond: 128000 },
  };

  // ── Audio helpers ──────────────────────────────────────────────────────────
  async function cleanupAudio() {
    try {
      if (recording) {
        await recording.stopAndUnloadAsync();
        setRecording(null);
      }
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });
    } catch {}
  }

  async function startRecording() {
    if (isProcessing || uploadInFlight.current) return;
    try {
      await cleanupAudio();
      setIsRecording(true);
      setStatusText("Listening...");
      setDecision(null);
      const { recording: newRecording } =
        await Audio.Recording.createAsync(recordingOptions);
      setRecording(newRecording);
    } catch (err) {
      console.error("Failed to start recording", err);
      setIsRecording(false);
      setStatusText("Mic error. Try again.");
    }
  }

  async function stopRecording() {
    if (!recording || !isRecording) return;
    setIsRecording(false);
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      if (uri) {
        // Android doesn't always flush the audio file immediately after stopAndUnloadAsync.
        // A short wait prevents the alternating "Network request failed" on consecutive commands.
        await new Promise<void>((r) => setTimeout(r, 250));
        uploadAudio(uri);
      }
    } catch (error) {
      console.error("Stop error:", error);
      setRecording(null);
      setStatusText("Hold the Button...");
    }
  }

  async function uploadAudio(uri: string) {
    if (uploadInFlight.current) return;
    uploadInFlight.current = true;
    setIsProcessing(true);
    setStatusText("Processing...");
    setDecision(null);

    const MAX_ATTEMPTS = 2;

    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
      const controller = new AbortController();
      abortControllerRef.current = controller;
      const timer = setTimeout(() => controller.abort(), VOICE_TIMEOUT_MS);

      try {
        const formData = new FormData();
        formData.append("file", {
          uri,
          name: "voice_command.wav",
          type: "audio/wav",
        } as any);

        const response = await fetch(`${API_URL}/process-voice`, {
          method: "POST",
          body: formData,
          signal: controller.signal,
        });

        clearTimeout(timer);
        const data = await readApiResponse(response);

        if (response.ok && data.status === "success") {
          setStatusText(
            `${data.action}: ${data.item} (${data.item_nepali})\nStock now: ${data.new_stock} ${data.unit}`,
          );
          setTranscription(
            data.transcription ? `"${data.transcription}"` : "—",
          );
          setDecision({
            action: data.action,
            item: data.item,
            item_nepali: data.item_nepali,
            qty_changed: data.qty_changed,
            new_stock: data.new_stock,
            unit: data.unit,
            alert_message: data.alert_message ?? null,
          });
        } else {
          setStatusText(
            getApiErrorMessage(data, "Could not process command."),
          );
          setTranscription(
            data.transcription ? `"${data.transcription}"` : "—",
          );
        }
        break;
      } catch (error: any) {
        clearTimeout(timer);
        if (error?.name !== "AbortError" && attempt < MAX_ATTEMPTS) {
          await new Promise<void>((r) => setTimeout(r, 400));
          continue;
        }
        setStatusText(
          error?.name === "AbortError"
            ? "Request timed out. Please try again."
            : "Cannot connect to server.",
        );
        console.error("Upload failed:", error);
        break;
      }
    }

    setIsProcessing(false);
    uploadInFlight.current = false;
  }

  async function handleFinish() {
    abortControllerRef.current?.abort();
    if (recording) {
      try {
        await recording.stopAndUnloadAsync();
      } catch {}
    }
    uploadInFlight.current = false;
    router.replace("/(tabs)");
  }

  // ── Derived state (only dynamic values that can't be static className) ─────
  const holdLabel = isProcessing
    ? "Please Wait..."
    : isRecording
      ? "Release to Send"
      : "Hold to Speak";

  // ══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════════════════════════

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />
      <StatusBar barStyle="light-content" backgroundColor="#007566" />

      <SafeAreaView className="flex-1 bg-[#007566]">
        <View className="flex-1 bg-[#007566] px-6 pt-4">
          <View className="mt-12 flex-row items-center">
            <Pressable
              accessibilityLabel="Go back"
              accessibilityRole="button"
              className="mr-2 h-11 w-11 items-center justify-center rounded-full bg-zinc-100"
              hitSlop={8}
              onPress={() => router.back()}
              style={({ pressed }) => (pressed ? { opacity: 0.8 } : null)}
            >
              <ArrowLeft color="#111827" size={22} strokeWidth={2.4} />
            </Pressable>
          </View>

          {/* ── Centre content ─────────────────────────────────────────────── */}
          <View className="flex-1 items-center justify-center">
            {/* Mic orb */}
            <View
              className={`p-10 rounded-full ${isRecording ? "bg-[#58CEAD]" : "bg-[#4BB5A3]"}`}
            >
              <Image
                source={Mic}
                style={{
                  width: 150,
                  height: 150,
                  opacity: isRecording ? 0.5 : 1,
                }}
                contentFit="contain"
              />
            </View>

            {/* Status */}
            <Text className="text-[22px] font-bold mt-10 text-white text-center">
              {isProcessing ? "Thinking..." : statusText}
            </Text>

            {/* Transcription */}
            <Text className="text-[#CCFBF1] font-medium mt-2 text-center px-4 italic">
              {transcription}
            </Text>

            {/* Decision card */}
            {decision && (
              <View className="mt-4 bg-white rounded-2xl p-4 w-full elevation-4">
                <Text className="text-gray-700 font-bold text-center text-sm mb-2.5">
                  ✅ Parsed Decision
                </Text>

                {/* 3-column stats */}
                <View className="flex-row gap-2.5">
                  {[
                    { label: "Action", value: decision.action },
                    { label: "Item", value: decision.item },
                    {
                      label: "Qty",
                      value: formatDecisionQuantity(decision),
                    },
                  ].map((stat) => (
                    <View
                      key={stat.label}
                      className="flex-1 bg-gray-50 rounded-xl p-2.5 items-center"
                    >
                      <Text className="text-[10px] text-gray-400 font-semibold uppercase tracking-wide mb-1">
                        {stat.label}
                      </Text>
                      <Text className="text-[13px] font-bold text-gray-900 text-center">
                        {stat.value}
                      </Text>
                    </View>
                  ))}
                </View>

                {/* Alert */}
                {decision.alert_message && (
                  <View className="mt-2.5 bg-amber-50 rounded-lg p-2.5">
                    <Text className="text-amber-800 text-xs font-medium">
                      ⚠️ {decision.alert_message}
                    </Text>
                  </View>
                )}
              </View>
            )}

            {/* Spinner */}
            {isProcessing && (
              <ActivityIndicator
                size="large"
                color="white"
                style={{ marginTop: 20 }}
              />
            )}
          </View>

          {/* ── Buttons ────────────────────────────────────────────────────── */}
          <View className={`${Platform.OS === "android" ? "mb-5" : "mb-2"}`}>
            {/* Hold to Speak
                – default:   white bg, teal border, teal text
                – recording: red bg,   red border,  white text
                – processing: light teal bg, dimmed              */}
            <Pressable
              disabled={isProcessing}
              onPressIn={startRecording}
              onPressOut={stopRecording}
              style={({ pressed }) => ({
                opacity: isProcessing ? 0.7 : pressed ? 0.9 : 1,
                transform: [{ scale: pressed ? 0.98 : 1 }],
              })}
              className={`w-full py-[18px] rounded-2xl border-2 mb-3 items-center justify-center
                elevation-6
                ${
                  isProcessing
                    ? "bg-[#DFF7F3] border-[#007566]"
                    : isRecording
                      ? "bg-red-500 border-red-300"
                      : "bg-white border-[#007566]"
                }`}
            >
              <Text
                className={`text-lg font-extrabold text-center tracking-wide
                  ${isRecording ? "text-white" : "text-[#007566]"}`}
              >
                {holdLabel}
              </Text>
            </Pressable>

            {/* Finish — transparent with white border */}
            <Pressable
              onPress={handleFinish}
              style={({ pressed }) => ({ opacity: pressed ? 0.8 : 1 })}
              className="w-full py-4 rounded-2xl border-2 border-white bg-transparent items-center justify-center"
            >
              <Text className="text-lg font-bold text-white text-center">
                Finish
              </Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    </>
  );
}
