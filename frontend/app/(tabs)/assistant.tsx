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
  Animated,
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
// QUICK ACTIONS — buttons that trigger predefined analysis
// ══════════════════════════════════════════════════════════════════════════════

const QUICK_ACTIONS: QuickAction[] = [
  {
    label: "Low Stock",
    icon: "warning",
    action: "low_stock",
    description: "Check items running low",
  },
  {
    label: "Today's Sales",
    icon: "bar-chart",
    action: "today_sales",
    description: "View today's activity",
  },
  {
    label: "Summary",
    icon: "insights",
    action: "summary",
    description: "Business health overview",
  },
  {
    label: "Top Products",
    icon: "star",
    action: "top_products",
    description: "Best sellers this month",
  },
  {
    label: "Restock",
    icon: "shopping-cart",
    action: "restock_advice",
    description: "What to order next",
  },
];

// ══════════════════════════════════════════════════════════════════════════════
// SIMPLE MARKDOWN-LIKE TEXT RENDERER
// ══════════════════════════════════════════════════════════════════════════════

function renderFormattedText(text: string, isAI: boolean) {
  // Split by lines and render each line
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];

  lines.forEach((line, lineIdx) => {
    const trimmed = line.trim();

    // Empty line → small spacer
    if (!trimmed) {
      elements.push(<View key={`s-${lineIdx}`} style={{ height: 6 }} />);
      return;
    }

    // Heading-like lines (### or ##)
    if (trimmed.startsWith("###")) {
      elements.push(
        <Text
          key={`h3-${lineIdx}`}
          style={{
            fontSize: 14,
            fontWeight: "700",
            color: isAI ? "#1F2937" : "white",
            marginTop: 6,
            marginBottom: 2,
          }}
        >
          {trimmed.replace(/^#{1,3}\s*/, "")}
        </Text>
      );
      return;
    }

    if (trimmed.startsWith("##")) {
      elements.push(
        <Text
          key={`h2-${lineIdx}`}
          style={{
            fontSize: 15,
            fontWeight: "800",
            color: isAI ? "#1F2937" : "white",
            marginTop: 8,
            marginBottom: 3,
          }}
        >
          {trimmed.replace(/^#{1,2}\s*/, "")}
        </Text>
      );
      return;
    }

    // Bullet points (- or • or *)
    if (/^[-•*]\s/.test(trimmed)) {
      const bulletText = trimmed.replace(/^[-•*]\s*/, "");
      elements.push(
        <View
          key={`b-${lineIdx}`}
          style={{ flexDirection: "row", marginTop: 2, paddingLeft: 4 }}
        >
          <Text
            style={{
              color: isAI ? "#7E22CE" : "rgba(255,255,255,0.8)",
              fontSize: 13,
              marginRight: 6,
              lineHeight: 20,
            }}
          >
            •
          </Text>
          <Text
            style={{
              flex: 1,
              color: isAI ? "#374151" : "white",
              fontSize: 13.5,
              lineHeight: 20,
            }}
          >
            {renderInlineFormatting(bulletText, isAI)}
          </Text>
        </View>
      );
      return;
    }

    // Numbered list (1. 2. etc.)
    const numberedMatch = trimmed.match(/^(\d+)\.\s(.+)/);
    if (numberedMatch) {
      elements.push(
        <View
          key={`n-${lineIdx}`}
          style={{ flexDirection: "row", marginTop: 2, paddingLeft: 4 }}
        >
          <Text
            style={{
              color: isAI ? "#7E22CE" : "rgba(255,255,255,0.8)",
              fontSize: 13,
              fontWeight: "700",
              marginRight: 6,
              lineHeight: 20,
              minWidth: 18,
            }}
          >
            {numberedMatch[1]}.
          </Text>
          <Text
            style={{
              flex: 1,
              color: isAI ? "#374151" : "white",
              fontSize: 13.5,
              lineHeight: 20,
            }}
          >
            {renderInlineFormatting(numberedMatch[2], isAI)}
          </Text>
        </View>
      );
      return;
    }

    // Regular text
    elements.push(
      <Text
        key={`t-${lineIdx}`}
        style={{
          color: isAI ? "#1F2937" : "white",
          fontSize: 14,
          lineHeight: 21,
          marginTop: 1,
        }}
      >
        {renderInlineFormatting(trimmed, isAI)}
      </Text>
    );
  });

  return elements;
}

/**
 * Handle **bold** inline formatting.
 */
function renderInlineFormatting(
  text: string,
  isAI: boolean
): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <Text
          key={i}
          style={{
            fontWeight: "800",
            color: isAI ? "#1F2937" : "white",
          }}
        >
          {part.slice(2, -2)}
        </Text>
      );
    }
    return <Text key={i}>{part}</Text>;
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// TYPING INDICATOR COMPONENT
// ══════════════════════════════════════════════════════════════════════════════

function TypingIndicator() {
  const dot1 = useRef(new Animated.Value(0)).current;
  const dot2 = useRef(new Animated.Value(0)).current;
  const dot3 = useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    const animate = (dot: Animated.Value, delay: number) => {
      return Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(dot, {
            toValue: 1,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.timing(dot, {
            toValue: 0,
            duration: 300,
            useNativeDriver: true,
          }),
        ])
      );
    };

    const a1 = animate(dot1, 0);
    const a2 = animate(dot2, 200);
    const a3 = animate(dot3, 400);

    a1.start();
    a2.start();
    a3.start();

    return () => {
      a1.stop();
      a2.stop();
      a3.stop();
    };
  }, []);

  const dotStyle = (anim: Animated.Value) => ({
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: "#7E22CE",
    marginHorizontal: 2,
    opacity: anim.interpolate({
      inputRange: [0, 1],
      outputRange: [0.3, 1],
    }),
    transform: [
      {
        translateY: anim.interpolate({
          inputRange: [0, 1],
          outputRange: [0, -4],
        }),
      },
    ],
  });

  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        paddingHorizontal: 20,
        paddingVertical: 12,
      }}
    >
      <View
        style={{
          width: 28,
          height: 28,
          borderRadius: 14,
          backgroundColor: "#7E22CE",
          alignItems: "center",
          justifyContent: "center",
          marginRight: 10,
        }}
      >
        <MaterialIcons name="psychology" size={16} color="white" />
      </View>
      <View
        style={{
          backgroundColor: "#F3F4F6",
          borderRadius: 16,
          borderTopLeftRadius: 4,
          paddingHorizontal: 16,
          paddingVertical: 12,
          flexDirection: "row",
          alignItems: "center",
        }}
      >
        <Animated.View style={dotStyle(dot1)} />
        <Animated.View style={dotStyle(dot2)} />
        <Animated.View style={dotStyle(dot3)} />
        <Text
          style={{
            marginLeft: 8,
            color: "#9CA3AF",
            fontSize: 12,
            fontStyle: "italic",
          }}
        >
          Thinking...
        </Text>
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
      text: "👋 Hello! I'm your **SmartBiz AI** assistant.\n\nI can help you with:\n• 📦 Stock levels & low stock alerts\n• 💰 Sales analysis & trends\n• 📈 Business insights & summaries\n• ⭐ Top product performance\n• 🛒 Restocking recommendations\n\nAsk me anything or tap a quick action below!",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const listRef = useRef<FlatList>(null);

  // ── Send message to backend ──────────────────────────────────────────────
  const sendMessage = useCallback(
    async (text?: string, action?: string) => {
      const messageText = text ?? input.trim();
      if (!messageText && !action) return;
      if (loading) return;

      // Build the user message
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

      // Build conversation history (exclude welcome message, last 6 messages)
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

        const aiMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "ai",
          text: data.reply ?? "Sorry, I could not generate a response.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      } catch (err: any) {
        clearTimeout(timer);
        const errMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "ai",
          text:
            err?.name === "AbortError"
              ? "⏳ Request timed out. The AI is taking too long — please try a simpler question or check if Ollama is running."
              : `⚠️ Could not connect to AI backend.\n\nMake sure:\n• Backend server is running (uvicorn)\n• Ollama is running with: \`ollama run qwen2.5:7b\`\n• Your device is on the same network`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setLoading(false);
        setTimeout(
          () => listRef.current?.scrollToEnd({ animated: true }),
          150
        );
      }
    },
    [input, messages, loading]
  );

  // ── Clear chat ─────────────────────────────────────────────────────────────
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

  // ── Render a single message bubble ────────────────────────────────────────
  const renderMessage = ({ item }: { item: Message }) => {
    const isAI = item.role === "ai";

    return (
      <View
        style={{
          alignSelf: isAI ? "flex-start" : "flex-end",
          maxWidth: "85%",
          marginVertical: 4,
          marginHorizontal: 12,
        }}
      >
        {/* AI avatar + label */}
        {isAI && (
          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              marginBottom: 4,
            }}
          >
            <View
              style={{
                width: 24,
                height: 24,
                borderRadius: 12,
                backgroundColor: "#7E22CE",
                alignItems: "center",
                justifyContent: "center",
                marginRight: 6,
              }}
            >
              <MaterialIcons name="psychology" size={14} color="white" />
            </View>
            <Text
              style={{ fontSize: 11, color: "#6B7280", fontWeight: "600" }}
            >
              SmartBiz AI
            </Text>
            <Text style={{ fontSize: 10, color: "#9CA3AF", marginLeft: 6 }}>
              {item.timestamp.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </Text>
          </View>
        )}

        {/* Message bubble */}
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
          {isAI ? (
            <View>{renderFormattedText(item.text, true)}</View>
          ) : (
            <Text
              style={{
                color: "white",
                fontSize: 14,
                lineHeight: 20,
              }}
            >
              {item.text}
            </Text>
          )}
        </View>

        {/* User message timestamp */}
        {!isAI && (
          <Text
            style={{
              fontSize: 10,
              color: "#9CA3AF",
              alignSelf: "flex-end",
              marginTop: 2,
              marginRight: 4,
            }}
          >
            {item.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </Text>
        )}
      </View>
    );
  };

  // ══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════════════════════════

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: "white" }}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={90}
    >
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <View
        style={{
          paddingTop: 56,
          paddingBottom: 12,
          paddingHorizontal: 16,
          borderBottomWidth: 1,
          borderBottomColor: "#F3F4F6",
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "flex-end",
        }}
      >
        <View>
          <Text
            style={{ fontSize: 22, fontWeight: "800", color: "#1F2937" }}
          >
            AI Assistant
          </Text>
          <Text style={{ fontSize: 12, color: "#6B7280", marginTop: 2 }}>
            Powered by Qwen 2.5 · Business Analyst
          </Text>
        </View>
        <Pressable
          onPress={clearChat}
          style={({ pressed }) => ({
            paddingHorizontal: 12,
            paddingVertical: 6,
            borderRadius: 16,
            backgroundColor: pressed ? "#FEE2E2" : "#FEF2F2",
            borderWidth: 1,
            borderColor: "#FECACA",
          })}
        >
          <Text style={{ color: "#DC2626", fontSize: 12, fontWeight: "600" }}>
            Clear
          </Text>
        </Pressable>
      </View>

      {/* ── Messages ───────────────────────────────────────────────────────── */}
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

      {/* ── Typing indicator ───────────────────────────────────────────────── */}
      {loading && <TypingIndicator />}

      {/* ── Quick Actions ──────────────────────────────────────────────────── */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ flexGrow: 0 }}
        contentContainerStyle={{
          paddingHorizontal: 12,
          paddingVertical: 8,
          gap: 8,
        }}
      >
        {QUICK_ACTIONS.map((qa) => (
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
              paddingHorizontal: 13,
              paddingVertical: 8,
              opacity: loading ? 0.5 : 1,
            })}
          >
            <MaterialIcons
              name={qa.icon as any}
              size={15}
              color="#7E22CE"
              style={{ marginRight: 5 }}
            />
            <Text
              style={{
                color: "#7E22CE",
                fontWeight: "600",
                fontSize: 13,
              }}
            >
              {qa.label}
            </Text>
          </Pressable>
        ))}
      </ScrollView>

      {/* ── Input Row ──────────────────────────────────────────────────────── */}
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
          placeholder="Ask about stock, sales, or business..."
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
            maxHeight: 100,
          }}
          multiline
          maxLength={500}
          onSubmitEditing={() => sendMessage()}
          returnKeyType="send"
          editable={!loading}
        />
        <Pressable
          onPress={() => sendMessage()}
          disabled={loading || !input.trim()}
          style={({ pressed }) => ({
            width: 44,
            height: 44,
            borderRadius: 22,
            backgroundColor:
              loading || !input.trim() ? "#E5E7EB" : "#7E22CE",
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
