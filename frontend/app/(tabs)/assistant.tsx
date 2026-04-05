import React, { useState, useRef, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Animated,
  StatusBar,
  SafeAreaView,
} from "react-native";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { API_URL, CHAT_TIMEOUT_MS } from "../../constants/Config";

// ══════════════════════════════════════════════════════════════════════════════
// TYPES
// ══════════════════════════════════════════════════════════════════════════════

type Message = {
  id: string;
  role: "user" | "ai";
  text: string;
  timestamp: Date;
};

type QuickAction = {
  label: string;
  icon: string;
  action: string;
  description: string;
};

// ══════════════════════════════════════════════════════════════════════════════
// QUICK ACTIONS
// ══════════════════════════════════════════════════════════════════════════════

const QUICK_ACTIONS: QuickAction[] = [
  { label: "Low Stock",     icon: "warning",       action: "low_stock",      description: "Check items running low" },
  { label: "Today's Sales", icon: "bar-chart",     action: "today_sales",    description: "View today's activity" },
  { label: "Summary",       icon: "insights",      action: "summary",        description: "Business health overview" },
  { label: "Top Products",  icon: "star",          action: "top_products",   description: "Best sellers this month" },
  { label: "Restock",       icon: "shopping-cart", action: "restock_advice", description: "What to order next" },
];

// ══════════════════════════════════════════════════════════════════════════════
// FORMATTED TEXT RENDERER
// ══════════════════════════════════════════════════════════════════════════════

function renderInlineFormatting(text: string, isAI: boolean): React.ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <Text key={i} className={`font-bold ${isAI ? "text-gray-900" : "text-white"}`}>
          {part.slice(2, -2)}
        </Text>
      );
    }
    return <Text key={i}>{part}</Text>;
  });
}

function renderFormattedText(text: string, isAI: boolean) {
  const elements: React.ReactNode[] = [];

  text.split("\n").forEach((line, idx) => {
    const t = line.trim();

    if (!t) {
      elements.push(<View key={`sp-${idx}`} className="h-1.5" />);
      return;
    }

    if (t.startsWith("###")) {
      elements.push(
        <Text key={`h3-${idx}`} className={`text-sm font-bold mt-1.5 mb-0.5 ${isAI ? "text-gray-900" : "text-white"}`}>
          {t.replace(/^#{1,3}\s*/, "")}
        </Text>
      );
      return;
    }

    if (t.startsWith("##")) {
      elements.push(
        <Text key={`h2-${idx}`} className={`text-[15px] font-extrabold mt-2 mb-1 ${isAI ? "text-gray-900" : "text-white"}`}>
          {t.replace(/^#{1,2}\s*/, "")}
        </Text>
      );
      return;
    }

    if (/^[-•*]\s/.test(t)) {
      elements.push(
        <View key={`b-${idx}`} className="flex-row mt-0.5 pl-1">
          <Text className={`text-[13px] mr-2 leading-5 ${isAI ? "text-[#007566]" : "text-white/70"}`}>•</Text>
          <Text className={`flex-1 text-[13.5px] leading-5 ${isAI ? "text-gray-700" : "text-white"}`}>
            {renderInlineFormatting(t.replace(/^[-•*]\s*/, ""), isAI)}
          </Text>
        </View>
      );
      return;
    }

    const nm = t.match(/^(\d+)\.\s(.+)/);
    if (nm) {
      elements.push(
        <View key={`n-${idx}`} className="flex-row mt-0.5 pl-1">
          <Text className={`text-[13px] font-bold mr-2 leading-5 min-w-[18px] ${isAI ? "text-[#007566]" : "text-white/70"}`}>
            {nm[1]}.
          </Text>
          <Text className={`flex-1 text-[13.5px] leading-5 ${isAI ? "text-gray-700" : "text-white"}`}>
            {renderInlineFormatting(nm[2], isAI)}
          </Text>
        </View>
      );
      return;
    }

    elements.push(
      <Text key={`t-${idx}`} className={`text-sm leading-[21px] mt-px ${isAI ? "text-gray-800" : "text-white"}`}>
        {renderInlineFormatting(t, isAI)}
      </Text>
    );
  });

  return elements;
}

// ══════════════════════════════════════════════════════════════════════════════
// TYPING INDICATOR
// ══════════════════════════════════════════════════════════════════════════════

function TypingIndicator() {
  const dot1 = useRef(new Animated.Value(0)).current;
  const dot2 = useRef(new Animated.Value(0)).current;
  const dot3 = useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    const anim = (dot: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(dot, { toValue: 1, duration: 300, useNativeDriver: true }),
          Animated.timing(dot, { toValue: 0, duration: 300, useNativeDriver: true }),
        ])
      );
    const a1 = anim(dot1, 0);
    const a2 = anim(dot2, 200);
    const a3 = anim(dot3, 400);
    a1.start(); a2.start(); a3.start();
    return () => { a1.stop(); a2.stop(); a3.stop(); };
  }, []);

  const dotStyle = (anim: Animated.Value) => ({
    width: 7, height: 7, borderRadius: 3.5,
    backgroundColor: "#007566",
    marginHorizontal: 2,
    opacity: anim.interpolate({ inputRange: [0, 1], outputRange: [0.3, 1] }),
    transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [0, -4] }) }],
  });

  return (
    <View className="flex-row items-center px-4 py-2.5">
      <View className="w-8 h-8 rounded-full bg-[#007566] items-center justify-center mr-2.5">
        <MaterialIcons name="psychology" size={16} color="white" />
      </View>
      <View className="bg-gray-100 rounded-2xl rounded-tl-[4px] px-4 py-3 flex-row items-center">
        <Animated.View style={dotStyle(dot1)} />
        <Animated.View style={dotStyle(dot2)} />
        <Animated.View style={dotStyle(dot3)} />
        <Text className="ml-2 text-gray-400 text-xs italic">Analyzing...</Text>
      </View>
    </View>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════════════════════

export default function AssistantScreen() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "ai",
      text: "👋 Hello! I'm your **Bikri AI** assistant.\n\nI can help you with:\n• 📦 Stock levels & low stock alerts\n• 💰 Sales analysis & trends\n• 📈 Business insights & summaries\n• ⭐ Top product performance\n• 🛒 Restocking recommendations\n\nAsk me anything or tap a quick action below!",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const listRef = useRef<FlatList>(null);

  // ── Send ──────────────────────────────────────────────────────────────────
  const sendMessage = useCallback(
    async (text?: string, action?: string) => {
      const messageText = text ?? input.trim();
      if (!messageText && !action) return;
      if (loading) return;

      const userMsg: Message = {
        id: Date.now().toString(),
        role: "user",
        text: action
          ? QUICK_ACTIONS.find((q) => q.action === action)?.label ?? messageText
          : messageText,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setLoading(true);

      const historyMessages = [...messages, userMsg]
        .filter((m) => m.id !== "welcome")
        .slice(-6)
        .map((m) => ({ role: m.role, text: m.text }));

      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS);

      try {
        const res = await fetch(`${API_URL}/api/chat/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: action ? null : messageText,
            action: action ?? null,
            history: historyMessages,
          }),
          signal: controller.signal,
        });

        clearTimeout(timer);
        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: "ai",
            text: data.reply ?? "Sorry, I could not generate a response.",
            timestamp: new Date(),
          },
        ]);
      } catch (err: any) {
        clearTimeout(timer);
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: "ai",
            text:
              err?.name === "AbortError"
                ? "⏳ Request timed out. Please try again or check if Ollama is running."
                : `⚠️ Could not connect.\n\nMake sure:\n• Backend server is running\n• Ollama is running with: \`ollama run qwen2.5:7b\`\n• Your device is on the same network`,
            timestamp: new Date(),
          },
        ]);
      } finally {
        setLoading(false);
        setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 150);
      }
    },
    [input, messages, loading]
  );

  // ── Clear ─────────────────────────────────────────────────────────────────
  const clearChat = useCallback(() => {
    setMessages([
      {
        id: "welcome",
        role: "ai",
        text: "🔄 Chat cleared! How can I help you?",
        timestamp: new Date(),
      },
    ]);
  }, []);

  // ── Message bubble ────────────────────────────────────────────────────────
  const renderMessage = ({ item }: { item: Message }) => {
    const isAI = item.role === "ai";
    const time = item.timestamp.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    return (
      <View className={`max-w-[85%] my-1 mx-3 ${isAI ? "self-start" : "self-end"}`}>

        {/* AI header */}
        {isAI && (
          <View className="flex-row items-center mb-1 gap-1.5">
            <View className="w-6 h-6 rounded-full bg-[#007566] items-center justify-center">
              <MaterialIcons name="psychology" size={13} color="white" />
            </View>
            <Text className="text-[11px] text-gray-500 font-semibold">Bikri AI</Text>
            <Text className="text-[10px] text-gray-400">{time}</Text>
          </View>
        )}

        {/* Bubble */}
        <View
          className={`px-3.5 py-2.5 rounded-2xl ${
            isAI ? "bg-gray-100 rounded-tl-[4px]" : "bg-[#007566] rounded-tr-[4px]"
          }`}
        >
          {isAI ? (
            <View>{renderFormattedText(item.text, true)}</View>
          ) : (
            <Text className="text-white text-sm leading-5">{item.text}</Text>
          )}
        </View>

        {/* User timestamp */}
        {!isAI && (
          <Text className="text-[10px] text-gray-400 self-end mt-0.5 mr-1">{time}</Text>
        )}
      </View>
    );
  };

  const canSend = !loading && !!input.trim();

  return (
    <SafeAreaView className="flex-1 bg-white">
      <StatusBar barStyle="dark-content" backgroundColor="white" />

      <KeyboardAvoidingView
        className="flex-1 bg-[#fff] mt-14 px-4"
              behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        {/* ── Header ───────────────────────────────────────────────────────── */}
        <View className="flex-row items-center justify-between px-4 pt-3 pb-3 border-b border-gray-100 bg-white">
          {/* Avatar + title */}
          <View className="flex-row items-center gap-3">
            <View className="w-10 h-10 rounded-2xl bg-[#007566] items-center justify-center">
              <MaterialIcons name="psychology" size={22} color="white" />
            </View>
            <View>
              <Text className="text-[18px] font-extrabold text-gray-900 leading-tight">
                Bikri Assistant
              </Text>
              <View className="flex-row items-center gap-1 mt-0.5">
                <View className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <Text className="text-[11px] text-gray-500">
                  Byapar ko Kurakani Suru Garum!
                </Text>
              </View>
            </View>
          </View>

          {/* Clear button */}
          <Pressable
            onPress={clearChat}
            style={({ pressed }) => ({ opacity: pressed ? 0.7 : 1 })}
            className="px-3 py-1.5 rounded-xl bg-red-50 border border-red-200"
          >
            <Text className="text-red-500 text-xs font-semibold">Clear</Text>
          </Pressable>
        </View>

        {/* ── Messages ─────────────────────────────────────────────────────── */}
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={renderMessage}
          contentContainerStyle={{ paddingVertical: 12, paddingBottom: 8 }}
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() =>
            listRef.current?.scrollToEnd({ animated: true })
          }
        />

        {/* ── Typing Indicator ─────────────────────────────────────────────── */}
        {loading && <TypingIndicator />}

        {/* ── Quick Actions ─────────────────────────────────────────────────── */}
        <View className="border-t border-gray-100">
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{
              paddingHorizontal: 12,
              paddingVertical: 10,
              gap: 8,
              alignItems: "center",
            }}
          >
            {QUICK_ACTIONS.map((qa) => (
              <Pressable
                key={qa.action}
                onPress={() => sendMessage(undefined, qa.action)}
                disabled={loading}
                style={({ pressed }) => ({
                  backgroundColor: pressed ? "#C7F5ED" : "#E6FFFB",
                  opacity: loading ? 0.45 : 1,
                })}
                className="flex-row items-center border border-[#BFEAE2] rounded-full px-3.5 py-2"
              >
                <MaterialIcons
                  name={qa.icon as any}
                  size={14}
                  color="#007566"
                  style={{ marginRight: 5 }}
                />
                <Text className="text-[#007566] text-xs font-semibold">{qa.label}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>

        {/* ── Input Row ────────────────────────────────────────────────────── */}
        <View className="flex-row items-center px-3 py-2.5 border-t border-gray-100 bg-white gap-2">
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder="Ask about stock, sales, or business..."
            placeholderTextColor="#9CA3AF"
            className="flex-1 bg-gray-50 border border-gray-200 rounded-3xl px-4 text-sm text-gray-800 max-h-[100px]"
            style={{
              paddingVertical: Platform.OS === "ios" ? 10 : 8,
              textAlignVertical: "center",
            }}
            multiline
            maxLength={500}
            onSubmitEditing={() => sendMessage()}
            returnKeyType="send"
            editable={!loading}
            blurOnSubmit
          />
          <Pressable
            onPress={() => sendMessage()}
            disabled={!canSend}
            style={({ pressed }) => ({
              backgroundColor: canSend ? "#007566" : "#E6FFFB",
              borderWidth: 1,
              borderColor: canSend ? "#007566" : "#B7E4DB",
              opacity: pressed && canSend ? 0.75 : 1,
            })}
            className="w-11 h-11 rounded-full items-center justify-center"
          >
            <MaterialIcons
              name="send"
              size={24}
              color={canSend ? "white" : "#007566"}
            />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
