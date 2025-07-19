import { useEffect, useState } from "react";
import VideoPlayer from "./VideoPlayer";

export default function Home() {
  const [targetIndex, setTargetIndex] = useState(null);
  const [isHandWaving, setIsHandWaving] = useState(false);

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
        console.log("🖐️ Hand waving triggered");
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
      />
    </div>
  );
}
