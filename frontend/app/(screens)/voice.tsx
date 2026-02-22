// frontend/app/voice.tsx
import { router, Stack } from "expo-router";
import React, { useState, useEffect } from "react";
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

// ✅ YOUR BACKEND IP
const API_URL = "http://192.168.1.95:8000";

const Mic = require("../../assets/images/purple_mic.png");

export default function Voice() {
  const [recording, setRecording] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const [aiResponse, setAiResponse] = useState("Hold the Button...");
  const [transcription, setTranscription] = useState("Ask about stock or sales");

  // NEW: store AI decision
  const [decision, setDecision] = useState(null);

  useEffect(() => {
    (async () => {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Permission missing", "Please allow microphone access.");
      }
    })();

    return () => {
      if (recording) recording.stopAndUnloadAsync();
    };
  }, []);

  const recordingOptions = {
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
    } catch (error) {
      console.log("Cleanup warning:", error);
    }
  }

  async function startRecording() {
    if (isProcessing) return;

    try {
      await cleanupAudio();
      setIsRecording(true);
      setAiResponse("Listening...");
      setDecision(null);

      const { recording: newRecording } = await Audio.Recording.createAsync(recordingOptions);
      setRecording(newRecording);
    } catch (err) {
      console.error("Failed to start recording", err);
      setIsRecording(false);
      setAiResponse("❌ Mic Error. Try again.");
    }
  }

  async function stopRecording() {
    if (!recording) return;

    setIsRecording(false);

    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      uploadAudio(uri);
    } catch (error) {
      console.error("Stop error:", error);
      setRecording(null);
    }
  }

  async function uploadAudio(uri) {
    if (!uri) return;

    setIsProcessing(true);
    setAiResponse("Processing...");
    setDecision(null);

    try {
      const formData = new FormData();
      formData.append("file", {
        uri,
        name: "voice_command.wav",
        type: "audio/wav",
      });

      const response = await fetch(`${API_URL}/process-voice`, {
        method: "POST",
        body: formData,
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      const data = await response.json();

      if (response.ok) {
        // 🔹 Update transcription and AI response
        setTranscription(data.transcription ? `"${data.transcription}"` : "—");
        setAiResponse(data.response || "No response");

        // 🔹 Show decision
        if (data.intent && data.item && data.qty && data.unit) {
          setDecision({
            intent: data.intent,
            item: data.item,
            qty: data.qty,
            unit: data.unit,
          });
        }
      } else {
        setAiResponse("❌ Error: " + (data.error || "Unknown error"));
      }
    } catch (error) {
      console.error("Upload failed:", error);
      setAiResponse("❌ Could not connect to server.");
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <>
      <Stack.Screen options={{ headerShown: false }} />

      <KeyboardAvoidingView
        className="flex-1 justify-center"
        behavior={Platform.select({ ios: "padding", android: undefined })}
      >
        <KeyboardAvoidingView
          className="flex-1 bg-[#7E22CE] p-6"
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          <View className="flex-1 items-center justify-center">
            <View
              className={`p-10 rounded-full ${
                isRecording ? "bg-red-100" : "bg-purple-50"
              }`}
            >
              <Image
                source={Mic}
                style={{
                  width: 150,
                  height: 150,
                  opacity: isRecording ? 0.5 : 1,
                }}
                resizeMode="contain"
              />
            </View>

            <Text className="text-3xl font-bold mt-10 text-white text-center">
              {isProcessing ? "Thinking..." : aiResponse}
            </Text>

            <Text className="text-purple-200 font-medium mt-2 text-center px-4 italic">
              {transcription}
            </Text>

            {decision && (
              <View className="mt-4 bg-white p-4 rounded-xl w-full">
                <Text className="text-gray-700 font-semibold text-center mb-2">
                  ✅ Parsed Decision
                </Text>
                <Text className="text-gray-800">
                  Action: {decision.intent}
                </Text>
                <Text className="text-gray-800">
                  Item: {decision.item}
                </Text>
                <Text className="text-gray-800">
                  Quantity: {decision.qty}
                </Text>
                <Text className="text-gray-800">
                  Unit: {decision.unit}
                </Text>
              </View>
            )}

            {isProcessing && (
              <ActivityIndicator
                size="large"
                color="white"
                className="mt-4"
              />
            )}
          </View>

          <View className="mb-6">
            <Pressable
              disabled={isProcessing}
              onPressIn={startRecording}
              onPressOut={stopRecording}
              style={({ pressed }) => ({
                opacity: pressed || isProcessing ? 0.8 : 1,
                transform: [{ scale: pressed ? 0.95 : 1 }],
              })}
              className={`mx-6 py-4 rounded-2xl shadow-lg ${
                isRecording ? "bg-red-500" : "bg-white"
              }`}
            >
              <Text
                className={`text-xl font-bold text-center ${
                  isRecording ? "text-white" : "text-[#7E22CE]"
                }`}
              >
                {isProcessing
                  ? "Please Wait..."
                  : isRecording
                  ? "Release to Send"
                  : "Hold to Speak"}
              </Text>
            </Pressable>
          </View>

          <View className="mb-8">
            <Pressable
              style={({ pressed }) => ({
                opacity: pressed ? 0.8 : 1,
              })}
              className="border-2 border-white mx-6 py-4 rounded-2xl"
              onPress={() => router.push("/(tabs)")}
            >
              <Text className="text-xl font-bold text-white text-center" on>
                Finish
              </Text>
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </KeyboardAvoidingView>
    </>
  );
}