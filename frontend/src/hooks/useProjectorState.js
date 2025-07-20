"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useThrottle } from "@uidotdev/usehooks";

const WEBSOCKET_URL = "ws://localhost:8000/ws/projector";
const COMMAND_THROTTLE_MS = 3000;

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

  const [lastCommand, setLastCommand] = useState(null);
  const throttledCommand = useThrottle(lastCommand, COMMAND_THROTTLE_MS);

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
        setLastCommand(message);
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
    if (!throttledCommand) {
      return;
    }

    if (
      throttledCommand.type === "SET_EMOTION" &&
      throttledCommand.payload.emotion
    ) {
      setEmotion(throttledCommand.payload.emotion);
    } else if (
      throttledCommand.type === "SET_MODE" &&
      throttledCommand.payload.mode
    ) {
      setMode(throttledCommand.payload.mode);
    }
  }, [throttledCommand]);

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
      let command = null;

      if (!isNaN(parseInt(key, 10)) && parseInt(key, 10) in EMOTION_MAP) {
        const newEmotion = EMOTION_MAP[parseInt(key, 10)];
        console.log(`Key '${key}' pressed, setting emotion to ${newEmotion}`);
        command = { type: "SET_EMOTION", payload: { emotion: newEmotion } };
      } else {
        let newMode = null;
        switch (key) {
          case "s":
            console.log("Key 's' pressed, setting mode to SLEEP");
            newMode = "SLEEP";
            break;
          case "w":
            console.log("Key 'w' pressed, setting mode to IDLE");
            newMode = "IDLE";
            break;
          case "r":
            console.log("Key 'r' pressed, setting mode to REWIND");
            newMode = "REWIND";
            break;
          case "f":
          case " ": // Space key for forget
            e.preventDefault();
            console.log("Key 'f' or space pressed, setting mode to FORGET");
            newMode = "FORGET";
            break;
          default:
            break;
        }
        if (newMode) {
          command = { type: "SET_MODE", payload: { mode: newMode } };
        }
      }

      if (command) {
        setLastCommand(command);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return { emotion, mode, isConnected };
} 