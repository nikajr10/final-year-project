import { router, Stack } from "expo-router";
import React, { useState, useEffect, useRef } from "react";
import {
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  View,
  ActivityIndicator,
  Alert,
} from "react-native";
import { Audio } from "expo-av";
import { API_URL } from "../../constants/Config";

// ✅ YOUR BACKEND IP

const Mic = require("../../assets/images/purple_mic.png");

type Decision = {
  action: string;
  item: string;
  item_nepali: string;
  qty_changed: number;
  new_stock: number;
  unit: string;
  alert_message: string | null;
};

const VOICE_TIMEOUT_MS = 15000;

export default function Voice() {
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const [statusText, setStatusText] = useState("Hold the Button...");
  const [decision, setDecision] = useState<Decision | null>(null);
  const [aiResponse, setAiResponse] = useState("Hold the Button...");
  const [transcription, setTranscription] = useState(
    "Ask about stock or sales",
  );

  // Prevent duplicate uploads when user releases/re-presses fast
  const uploadInFlight = useRef(false);

  useEffect(() => {
    (async () => {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Permission missing", "Please allow microphone access.");
      }
    })();

    return () => {
      // Clean up on unmount
      if (recording) recording.stopAndUnloadAsync().catch(() => {});
    };
  }, []);

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
    web: {
      mimeType: "audio/wav",
      bitsPerSecond: 128000,
    },
  };

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
    } catch {
      // ignore cleanup errors
    }
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
      if (uri) uploadAudio(uri);
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

    const controller = new AbortController();
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
      const data = await response.json();

      if (response.ok && data.status === "success") {
        // Build a human-readable status line from the actual backend fields
        const msg =
          `${data.action}: ${data.item} (${data.item_nepali})\n` +
          `Stock now: ${data.new_stock} ${data.unit}`;
        setStatusText(msg);
        setTranscription(data.transcription ? `"${data.transcription}"` : "—");
        setDecision({
          action:       data.action,
          item:         data.item,
          item_nepali:  data.item_nepali,
          qty_changed:  data.qty_changed,
          new_stock:    data.new_stock,
          unit:         data.unit,
          alert_message: data.alert_message ?? null,
        });
      } else {
        setStatusText(data.message || data.error || "Could not process command.");
        setTranscription(data.transcription ? `"${data.transcription}"` : "—");
      }
    } catch (error: any) {
      clearTimeout(timer);
      if (error?.name === "AbortError") {
        setStatusText("Request timed out. Please try again.");
      } else {
        setStatusText("Cannot connect to server.");
      }
      console.error("Upload failed:", error);
    } finally {
      setIsProcessing(false);
      uploadInFlight.current = false;
    }
  }

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.select({ ios: "padding", android: undefined })}
      >
        <KeyboardAvoidingView
          style={{ flex: 1, backgroundColor: "#7E22CE", padding: 24 }}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
            <View
              style={{
                padding: 40,
                borderRadius: 9999,
                backgroundColor: isRecording ? "#FEE2E2" : "#F5F3FF",
              }}
            >
              <Image
                source={Mic}
                style={{ width: 150, height: 150, opacity: isRecording ? 0.5 : 1 }}
                resizeMode="contain"
              />
            </View>

            <Text
              style={{
                fontSize: 22,
                fontWeight: "bold",
                marginTop: 40,
                color: "white",
                textAlign: "center",
              }}
            >
              {isProcessing ? "Thinking..." : statusText}
            </Text>

            <Text
              style={{
                color: "#E9D5FF",
                fontWeight: "500",
                marginTop: 8,
                textAlign: "center",
                paddingHorizontal: 16,
                fontStyle: "italic",
              }}
            >
              {transcription}
            </Text>

            {decision && (
              <View className="mt-4 bg-white p-4 rounded-xl w-full">
                <Text className="text-gray-700 font-semibold text-center mb-2">
                  ✅ Parsed Decision
                </Text>
                <Text className="text-gray-800">Action: {decision.action}</Text>
                <Text className="text-gray-800">Item: {decision.item}</Text>
                <Text className="text-gray-800">Quantity: {decision.qty_changed}</Text>
                <Text className="text-gray-800">Unit: {decision.unit}</Text>
              </View>
            )}

            {isProcessing && (
              <ActivityIndicator size="large" color="white" className="mt-4" />
            )}
          </View>

          {/* Hold to Speak */}
          <View style={{ marginBottom: 24 }}>
            <Pressable
              disabled={isProcessing}
              onPressIn={startRecording}
              onPressOut={stopRecording}
              style={({ pressed }) => ({
                opacity: pressed || isProcessing ? 0.8 : 1,
                transform: [{ scale: pressed ? 0.95 : 1 }],
                marginHorizontal: 24,
                paddingVertical: 16,
                borderRadius: 16,
                backgroundColor: isRecording ? "#EF4444" : "white",
                shadowColor: "#000",
                shadowOpacity: 0.15,
                shadowRadius: 8,
                elevation: 4,
                alignItems: "center",
              })}
            >
              <Text
                style={{
                  fontSize: 18,
                  fontWeight: "bold",
                  color: isRecording ? "white" : "#7E22CE",
                }}
              >
                {isProcessing
                  ? "Please Wait..."
                  : isRecording
                    ? "Release to Send"
                    : "Hold to Speak"}
              </Text>
            </Pressable>
          </View>

          {/* Finish */}
          <View style={{ marginBottom: 32 }}>
            <Pressable
              style={({ pressed }) => ({
                opacity: pressed ? 0.8 : 1,
                marginHorizontal: 24,
                paddingVertical: 16,
                borderRadius: 16,
                borderWidth: 2,
                borderColor: "white",
                alignItems: "center",
              })}
              onPress={() => router.push("/(tabs)")}
            >
              <Text
                className="text-xl font-bold text-white text-center"
              >
                Finish
              </Text>
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </KeyboardAvoidingView>
    </>
  );
}

function setStatusText(arg0: string) {
  throw new Error("Function not implemented.");
}
