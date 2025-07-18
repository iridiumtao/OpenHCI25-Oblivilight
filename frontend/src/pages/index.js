import { useState } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import VideoPlayer from "./VideoPlayer";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export default function Home() {
  const [targetIndex, setTargetIndex] = useState(null);

  const triggerRandom = () => {
    const random = Math.floor(Math.random() * 10);
    console.log("🔀 Random target:", random+1);
    setTargetIndex(random);
  };

  return (
    <div>
      <VideoPlayer index={targetIndex} />
      <button
        onClick={triggerRandom}
        className="absolute top-4 left-4 bg-white text-black px-4 py-2 rounded"
      >
        隨機切換影片
      </button>
    </div>
  );
}