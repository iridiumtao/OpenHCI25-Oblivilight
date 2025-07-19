import React, { useEffect, useRef, useState } from 'react';
import clsx from 'clsx';

const videos = [
  "videos/neutral.mp4",
  "videos/happy.mp4",
  "videos/sad.mp4",
  "videos/warm.mp4",
  "videos/optimistic.mp4",
  "videos/anxious.mp4",
  "videos/peaceful.mp4",
  "videos/depressed.mp4",
  "videos/lonely.mp4",
  "videos/angry.mp4",
];

export default function VideoPlayer({ index = 0 }) {
  const videoRef = useRef(null);
  const [currentIndex, setCurrentIndex] = useState(index);
  const [fade, setFade] = useState(false);

  useEffect(() => {
    if (index !== currentIndex) {
      setFade(true); // 開始淡出
      const timeout = setTimeout(() => {
        setCurrentIndex(index); // 換影片
        setFade(false); // 淡入
      }, 400); // 淡出時間（ms）

      return () => clearTimeout(timeout);
    }
  }, [index, currentIndex]);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.load();
      videoRef.current.play().catch((e) => {
        console.warn('Auto-play blocked', e);
      });
    }
  }, [currentIndex]);

  const videoSrc = videos[Math.max(0, Math.min(currentIndex, videos.length - 1))];

  return (
    <div
      className={clsx(
        'transition-opacity duration-500 ease-in-out',
        fade ? 'opacity-0' : 'opacity-100'
      )}
    >
      <video
        ref={videoRef}
        key={videoSrc} // 確保重新載入
        loop
        controls={false}
        muted
        autoPlay
        className="w-full h-full object-cover absolute inset-0"
      >
        <source src={videoSrc} type="video/mp4" />
        你的瀏覽器不支援 HTML5 video。
      </video>
    </div>
  );
}