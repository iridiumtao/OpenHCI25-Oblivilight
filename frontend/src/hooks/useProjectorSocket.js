import { useEffect, useRef, useState } from "react";

const emotionMap = {
  happy: 1,
  sad: 2,
  warm: 3,
  optimistic: 4,
  anxious: 5,
  peaceful: 6,
  depressed: 7,
  lonely: 8,
  angry: 9,
  neutral: 0,
};

const emotionInterval = 10000; // 每 10 秒更新一次 emotion

/**
 * 負責與後端 WebSocket 連線，並提供即時的 emotion 和 mode 狀態
 * @param {string} wsUrl WebSocket 伺服器 URL
 */
export function useProjectorSocket(wsUrl) {
  const wsRef = useRef(null);
  const latestEmotionRef = useRef(null);

  const [emotionIndex, setEmotionIndex] = useState(null);
  const [mode, setMode] = useState("IDLE"); // "IDLE" | "SLEEP" | "FORGET"
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const connect = () => {
      // 防止在開發模式下 StrictMode 造成重複連線
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        return;
      }

      wsRef.current = new window.WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log("✅ WebSocket connected");
        setIsConnected(true);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("📩 WebSocket message received:", data);

          if (data.type === "SET_EMOTION" && data.payload?.emotion) {
            const emotionKey = data.payload.emotion.toLowerCase();
            if (emotionKey in emotionMap) {
              latestEmotionRef.current = emotionMap[emotionKey];
            } else {
              console.warn(`Unknown emotion: ${data.payload.emotion}`);
            }
          } else if (data.type === "SET_MODE" && data.payload?.mode) {
            setMode(data.payload.mode);
          }
        } catch (e) {
          console.error("Invalid JSON:", event.data);
        }
      };

      wsRef.current.onclose = () => {
        console.log("❌ WebSocket disconnected. Retrying in 3 seconds...");
        setIsConnected(false);
        // 清理 ref，確保下次 connect 能建立新實例
        wsRef.current = null;
        setTimeout(connect, 3000); // 3 秒後自動重連
      };

      wsRef.current.onerror = (err) => {
        console.error("WebSocket error:", err);
        // onclose 會在 error 後被觸發，所以這裡不用特別處理重連
        wsRef.current.close();
      };
    };

    connect();

    // Cleanup function
    return () => {
      if (wsRef.current) {
        // 移除 onclose listener，避免在元件卸載時觸發重連邏輯
        wsRef.current.onclose = null; 
        wsRef.current.close();
      }
    };
  }, [wsUrl]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (latestEmotionRef.current !== null) {
        setEmotionIndex(latestEmotionRef.current);
        latestEmotionRef.current = null;
      }
    }, emotionInterval);

    return () => clearInterval(timer);
  }, []);

  return { emotionIndex, mode, isConnected };
} 