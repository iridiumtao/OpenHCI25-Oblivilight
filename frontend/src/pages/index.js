import { useState } from "react";
import VideoPlayer from "./VideoPlayer";

export default function Home() {
  const [targetIndex, setTargetIndex] = useState(null);
  const [isHandWaving, setIsHandWaving] = useState(false);

  const triggerRandom = () => {
    const random = Math.floor(Math.random() * 10);
    console.log("🔀 Random target:", random + 1);
    setTargetIndex(random);
  };

  return (
    <div>
      <VideoPlayer 
        index={targetIndex} 
        isHandWaving={isHandWaving} 
        onHandWavingChange={setIsHandWaving}
      />
      <button
        onClick={triggerRandom}
        className="absolute top-4 left-4 bg-white text-black px-4 py-2 rounded z-30"
      >
        隨機切換影片
      </button>
      <button
        onClick={() => setIsHandWaving(true)}
        className="absolute top-16 left-4 bg-white text-black px-4 py-2 rounded z-30"
      >
        模擬 hand waving
      </button>
    </div>
  );
}