import React, { useState, useRef, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { useFocusEffect } from "expo-router";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { API_URL} from "../../constants/Config";

type Message = {
  id: string;
  role: "user" | "ai";
  text: string;
};

type QuickAction = {
  label: string;
  icon: string;
  action: string;
};

const QUICK_ACTIONS: QuickAction[] = [
  { label: "Low Stock Alert", icon: "warning", action: "low_stock" },
  { label: "Today's Sales",   icon: "bar-chart", action: "today_sales" },
  { label: "Business Summary", icon: "insights", action: "summary" },
];

export default function AssistantScreen() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "0",
      role: "ai",
      text: "👋 Hello! I'm your **SmartBiz AI** assistant.\n\nI can help you with:\n• 📦 Low stock alerts\n• 💰 Sales analysis\n• 📈 Business insights\n\nAsk me anything or use the quick actions below!",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const listRef = useRef<FlatList>(null);

  const sendMessage = useCallback(async (text?: string, action?: string) => {
    const messageText = text ?? input.trim();
    if (!messageText && !action) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      text: action ? QUICK_ACTIONS.find(q => q.action === action)?.label ?? messageText : messageText,
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 100000);

    try {
      const res = await fetch(`${API_URL}/api/chat/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: action ? null : messageText, action: action ?? null }),
        signal: controller.signal,
      });

      clearTimeout(timer);
      const data = await res.json();

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "ai",
        text: data.reply ?? "Sorry, I could not generate a response.",
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err: any) {
      clearTimeout(timer);
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "ai",
        text: err?.name === "AbortError"
          ? "⚠️ Request timed out. Please try again."
          : "⚠️ Could not connect to AI. Make sure Ollama is running with `ollama run qwen2.5:7b`.",
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setLoading(false);
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [input]);

  const renderMessage = ({ item }: { item: Message }) => {
    const isAI = item.role === "ai";
    return (
      <View
        style={{
          alignSelf: isAI ? "flex-start" : "flex-end",
          maxWidth: "82%",
          marginVertical: 4,
          marginHorizontal: 12,
        }}
      >
        {isAI && (
          <View style={{ flexDirection: "row", alignItems: "center", marginBottom: 4 }}>
            <View style={{ width: 24, height: 24, borderRadius: 12, backgroundColor: "#7E22CE", alignItems: "center", justifyContent: "center", marginRight: 6 }}>
              <MaterialIcons name="psychology" size={14} color="white" />
            </View>
            <Text style={{ fontSize: 11, color: "#6B7280", fontWeight: "600" }}>SmartBiz AI</Text>
          </View>
        )}
        <View
          style={{
            backgroundColor: isAI ? "#F3F4F6" : "#7E22CE",
            borderRadius: 16,
            borderTopLeftRadius: isAI ? 4 : 16,
            borderTopRightRadius: isAI ? 16 : 4,
            paddingHorizontal: 14,
            paddingVertical: 10,
          }}
        >
          <Text style={{ color: isAI ? "#1F2937" : "white", fontSize: 14, lineHeight: 20 }}>
            {item.text}
          </Text>
        </View>
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: "white" }}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={90}
    >
      {/* Header */}
      <View style={{ paddingTop: 56, paddingBottom: 12, paddingHorizontal: 16, borderBottomWidth: 1, borderBottomColor: "#F3F4F6" }}>
        <Text style={{ fontSize: 22, fontWeight: "800", color: "#1F2937" }}>AI Assistant</Text>
        <Text style={{ fontSize: 13, color: "#6B7280", marginTop: 2 }}>Powered by Qwen 2.5</Text>
      </View>

      {/* Messages */}
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={item => item.id}
        renderItem={renderMessage}
        contentContainerStyle={{ paddingVertical: 12, paddingBottom: 8 }}
        showsVerticalScrollIndicator={false}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
      />

      {/* Loading indicator */}
      {loading && (
        <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: 20, paddingVertical: 8 }}>
          <View style={{ width: 24, height: 24, borderRadius: 12, backgroundColor: "#7E22CE", alignItems: "center", justifyContent: "center", marginRight: 8 }}>
            <MaterialIcons name="psychology" size={14} color="white" />
          </View>
          <View style={{ backgroundColor: "#F3F4F6", borderRadius: 16, paddingHorizontal: 14, paddingVertical: 10 }}>
            <ActivityIndicator size="small" color="#7E22CE" />
          </View>
        </View>
      )}

      {/* Quick Actions */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ flexGrow: 0 }}
        contentContainerStyle={{ paddingHorizontal: 12, paddingVertical: 8, gap: 8 }}
      >
        {QUICK_ACTIONS.map(qa => (
          <Pressable
            key={qa.action}
            onPress={() => sendMessage(undefined, qa.action)}
            disabled={loading}
            style={({ pressed }) => ({
              flexDirection: "row",
              alignItems: "center",
              backgroundColor: pressed ? "#EDE9FE" : "#F5F3FF",
              borderWidth: 1,
              borderColor: "#DDD6FE",
              borderRadius: 20,
              paddingHorizontal: 12,
              paddingVertical: 7,
              opacity: loading ? 0.5 : 1,
            })}
          >
            <MaterialIcons name={qa.icon as any} size={15} color="#7E22CE" style={{ marginRight: 5 }} />
            <Text style={{ color: "#7E22CE", fontWeight: "600", fontSize: 13 }}>{qa.label}</Text>
          </Pressable>
        ))}
      </ScrollView>

      {/* Input Row */}
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          paddingHorizontal: 12,
          paddingVertical: 10,
          borderTopWidth: 1,
          borderTopColor: "#F3F4F6",
          backgroundColor: "white",
        }}
      >
        <TextInput
          value={input}
          onChangeText={setInput}
          placeholder="Ask anything about your business..."
          placeholderTextColor="#9CA3AF"
          style={{
            flex: 1,
            backgroundColor: "#F9FAFB",
            borderWidth: 1,
            borderColor: "#E5E7EB",
            borderRadius: 24,
            paddingHorizontal: 16,
            paddingVertical: 10,
            fontSize: 14,
            color: "#1F2937",
            marginRight: 8,
          }}
          multiline
          maxLength={500}
          onSubmitEditing={() => sendMessage()}
          returnKeyType="send"
        />
        <Pressable
          onPress={() => sendMessage()}
          disabled={loading || !input.trim()}
          style={({ pressed }) => ({
            width: 44,
            height: 44,
            borderRadius: 22,
            backgroundColor: loading || !input.trim() ? "#E5E7EB" : "#7E22CE",
            alignItems: "center",
            justifyContent: "center",
            opacity: pressed ? 0.8 : 1,
          })}
        >
          <MaterialIcons name="send" size={20} color="white" />
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}
