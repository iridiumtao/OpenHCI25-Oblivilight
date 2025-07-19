import { useEffect, useState } from "react";
import VideoPlayer from "./VideoPlayer";
import { useProjectorSocket } from "../hooks/useProjectorSocket";

const WEBSOCKET_URL = "ws://localhost:8000/ws/projector";

export default function Home() {
  const [targetIndex, setTargetIndex] = useState(null);
  const [isHandWaving, setIsHandWaving] = useState(false);
  const [isSleeping, setIsSleeping] = useState(false);

  // --- WebSocket aio ---
  const { emotionIndex, mode, isConnected } = useProjectorSocket(WEBSOCKET_URL);

  useEffect(() => {
    if (typeof emotionIndex === "number") {
      console.log(`🎬 Emotion from WebSocket: ${emotionIndex}`);
      setTargetIndex(emotionIndex);
    }
  }, [emotionIndex]);

  useEffect(() => {
    console.log(`🖥️ Mode from WebSocket: ${mode}`);
    if (mode === "FORGET") {
      setIsHandWaving(true);
    }
    setIsSleeping(mode === "SLEEP");
  }, [mode]);


  // --- Keyboard simulation ---
  useEffect(() => {
    const handleKeyDown = (e) => {
      const key = e.key;

      if (key >= "0" && key <= "9") {
        const newIndex = parseInt(key, 10);
        console.log("🎯 Index from key:", newIndex);
        setTargetIndex(newIndex);
      }

      if (key === " ") {
        e.preventDefault(); // 避免網頁滑動
        console.log("🖐️ Hand waving triggered by key");
        setIsHandWaving(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div>
      <VideoPlayer
        index={targetIndex}
        isHandWaving={isHandWaving}
        onHandWavingChange={setIsHandWaving}
        isSleeping={isSleeping}
      />
      <div className="absolute top-4 left-4 bg-black/50 text-white px-3 py-1.5 rounded-lg text-sm z-30">
        WebSocket:{" "}
        <span className={isConnected ? "text-green-400" : "text-red-400"}>
          {isConnected ? "Connected" : "Disconnected"}
        </span>
      </div>
    </div>
  );
}
