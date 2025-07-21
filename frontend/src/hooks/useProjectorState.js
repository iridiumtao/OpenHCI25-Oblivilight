"use client";

import { useState, useEffect, useRef, useCallback } from "react";

const WEBSOCKET_URL = "ws://localhost:8000/ws/projector";

const EMOTION_MAP = {
  0: "neutral",
  1: "happy",
  2: "sad",
  3: "warm",
  4: "optimistic",
  5: "anxious",
  6: "peaceful",
  7: "depressed",
  8: "lonely",
  9: "angry",
};

export function useProjectorState() {
  const [emotion, setEmotion] = useState("neutral");
  const [mode, setMode] = useState("IDLE");
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  const connect = useCallback(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      return;
    }

    ws.current = new WebSocket(WEBSOCKET_URL);

    ws.current.onopen = () => {
      console.log("WebSocket Connected");
      setIsConnected(true);
    };

    ws.current.onclose = () => {
      console.log("WebSocket Disconnected");
      setIsConnected(false);
      setTimeout(connect, 5000); // Attempt to reconnect every 5 seconds
    };

    ws.current.onerror = (error) => {
      console.error("WebSocket Error:", error);
      ws.current.close();
    };

    ws.current.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log("🎬 Received command:", message);

        if (message.type === "SET_EMOTION" && message.payload.emotion) {
          setEmotion(message.payload.emotion);
        } else if (message.type === "SET_MODE" && message.payload.mode) {
          setMode(message.payload.mode);
        }
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  useEffect(() => {
    // Auto-reset temporary modes back to IDLE
    if (mode === "FORGET") {
      const timer = setTimeout(() => {
        setMode("IDLE");
      }, 5000); // 5 seconds for FORGET effect
      return () => clearTimeout(timer);
    }
    if (mode === "REWIND") {
      const timer = setTimeout(() => {
        setMode("IDLE");
      }, 10000); // 10 seconds for REWIND effect
      return () => clearTimeout(timer);
    }
  }, [mode]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      const key = e.key.toLowerCase();

      if (!isNaN(parseInt(key, 10)) && parseInt(key, 10) in EMOTION_MAP) {
        const newEmotion = EMOTION_MAP[parseInt(key, 10)];
        console.log(`Key '${key}' pressed, setting emotion to ${newEmotion}`);
        setEmotion(newEmotion);
      } else {
        switch (key) {
          case "s":
            console.log("Key 's' pressed, setting mode to SLEEP");
            setMode("SLEEP");
            break;
          case "w":
            console.log("Key 'w' pressed, setting mode to IDLE");
            setMode("IDLE");
            break;
          case "r":
            console.log("Key 'r' pressed, setting mode to REWIND");
            setMode("REWIND");
            break;
          case "f":
          case " ": // Space key for forget
            e.preventDefault();
            console.log("Key 'f' or space pressed, setting mode to FORGET");
            setMode("FORGET");
            break;
          default:
            break;
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return { emotion, mode, isConnected };
} 