"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import clsx from "clsx";
import { useProjectorState } from "../hooks/useProjectorState";

// Dynamically import VideoPlayer to avoid SSR issues with video elements
const VideoPlayer = dynamic(() => import("../components/VideoPlayer"), {
  ssr: false,
});

function StatusIndicator({ isConnected }) {
  return (
    <div className="absolute top-4 left-4 bg-black/50 text-white px-3 py-1.5 rounded-lg text-sm z-30">
      WebSocket:{" "}
      <span className={isConnected ? "text-green-400" : "text-red-400"}>
        {isConnected ? "Connected" : "Disconnected"}
      </span>
    </div>
  );
}

function ModeOverlay({ mode }) {
  const [isRewindVisible, setIsRewindVisible] = useState(false);
  const [isForgetVisible, setIsForisVisible] = useState(false);
  const [isSleepVisible, setIsSleepVisible] = useState(false);

  useEffect(() => {
    setIsRewindVisible(mode === "REWIND");
    setIsForisVisible(mode === "FORGET");
    setIsSleepVisible(mode === "SLEEP");
  }, [mode]);

  return (
    <>
      {/* Sleep Blackout */}
      <div
        className={clsx(
          "absolute inset-0 z-10 bg-black transition-opacity duration-1000",
          isSleepVisible ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
      />

      {/* Rewind Effect */}
      <div
        className={clsx(
          "absolute inset-0 z-20 flex items-center justify-center transition-opacity duration-500",
          isRewindVisible ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
      >
        <div className="text-white text-6xl font-bold animate-pulse">
          REWIND
        </div>
      </div>

      {/* Forget Effect */}
      <div
        className={clsx(
          "absolute inset-0 z-30 bg-white",
          isForgetVisible ? "animate-fade-in-out" : "opacity-0 pointer-events-none"
        )}
      />
    </>
  );
}

export default function Home() {
  const { emotion, mode, isConnected } = useProjectorState();

  const emotionToPlay =
    mode === "IDLE" || mode === "REWIND" ? emotion : "neutral";

  return (
    <main className="relative w-screen h-screen bg-black overflow-hidden">
      <StatusIndicator isConnected={isConnected} />
      <VideoPlayer emotion={emotionToPlay} />
      <ModeOverlay mode={mode} />
    </main>
  );
} 