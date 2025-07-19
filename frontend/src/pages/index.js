import { useEffect, useState } from "react";
import VideoPlayer from "./VideoPlayer";
import RewindPlayer from "./RewindPlayer";
import { useProjectorSocket } from "../hooks/useProjectorSocket";

const WEBSOCKET_URL = "ws://localhost:8000/ws/projector";

export default function Home() {
  const [targetIndex, setTargetIndex] = useState(null);
  const [isHandWaving, setIsHandWaving] = useState(false);
  const [isSleeping, setIsSleeping] = useState(false);
  const [isRewindActivated, setIsRewindActivated] = useState(false);
  const [showRewind, setShowRewind] = useState(false);
  const [showBlackout, setShowBlackout] = useState(false);

  // --- WebSocket aio ---
  const { emotionIndex, mode, isConnected } = useProjectorSocket(WEBSOCKET_URL);

  useEffect(() => {
    if (typeof emotionIndex === "number") {
      console.log(`🎬 Emotion from WebSocket: ${emotionIndex}`);
      setTargetIndex(emotionIndex);
    }
  }, [emotionIndex]);

  useEffect(() => {
    if (isRewindActivated) {
      // 啟動黑幕
      setShowBlackout(true);

      // 短暫延遲後顯示 RewindPlayer
      const showRewindTimer = setTimeout(() => {
        setShowRewind(true);
      }, 700); // 黑幕出現 300ms 後顯示 RewindPlayer

      // 5秒後結束 rewind
      const endRewindTimer = setTimeout(() => {
        setIsRewindActivated(false);
      }, 10000);

      return () => {
        clearTimeout(showRewindTimer);
        clearTimeout(endRewindTimer);
      };
    } else {
      // 結束時的處理
      const hideRewindTimer = setTimeout(() => {
        setShowRewind(false);
        // RewindPlayer 隱藏後再隱藏黑幕
        setTimeout(() => {
          setShowBlackout(false);
        }, 300);
      }, 300);

      return () => clearTimeout(hideRewindTimer);
    }
  }, [isRewindActivated]);

  useEffect(() => {
    console.log(`🖥️ Mode from WebSocket: ${mode}`);
    if (mode === "FORGET") {
      setIsHandWaving(true);
    }
    setIsSleeping(mode === "SLEEP");

    setIsRewindActivated(mode === "REWIND");

    if (mode === "WAKEUP") {
      setIsSleeping(false);
    }

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

      if (key.toLowerCase() === "r") {
        console.log("⏪ Rewind activated by key");
        setIsRewindActivated(true);
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
      />

      <div
        className={`absolute top-0 left-0 w-full h-full transition-opacity duration-300 ${
          isRewindActivated && showRewind ? "opacity-100 z-20" : "opacity-0 z-0"
        }`}
      >
        <RewindPlayer />
      </div>

      <div
        className={`absolute top-0 left-0 w-full h-full bg-black transition-opacity duration-300 ${
          showBlackout || isSleeping
            ? "opacity-100 z-10"
            : "opacity-0 z-0 pointer-events-none"
        }`}
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
