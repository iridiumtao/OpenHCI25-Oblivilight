import { useEffect, useRef, useState } from "react";

function VideoPlayer({ index, isHandWaving = false, onHandWavingChange }) {
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

  const interval = 10000; // 必須播放滿 10 秒 3 second is for testing
  const transitionDuration = 1500;
  const handWavingDuration = 10000; // 10 秒遮罩持續時間

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isSecondActive, setIsSecondActive] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [showHandWavingOverlay, setShowHandWavingOverlay] = useState(false);

  const [videoA, setVideoA] = useState(videos[0]);
  const [videoB, setVideoB] = useState("");

  const videoARef = useRef(null);
  const videoBRef = useRef(null);

  const nextIndexFromPropRef = useRef(null); // 用來儲存最新的 props.index
  const timerRef = useRef(null);
  const handWavingTimerRef = useRef(null);

  // 持續監聽 props.index 並更新 nextIndexFromPropRef
  useEffect(() => {
    if (typeof index === "number" && index >= 0 && index < videos.length) {
      nextIndexFromPropRef.current = index;
    }
  }, [index]);

  // 處理 isHandWaving 變化
  useEffect(() => {
    if (isHandWaving && !showHandWavingOverlay) {
      console.log("🫷 Hand waving started");
      // 開始手勢遮罩
      setShowHandWavingOverlay(true);

      // 重置當前播放影片的播放時間
      const currentVideoRef = isSecondActive ? videoBRef : videoARef;
      if (currentVideoRef.current) {
        currentVideoRef.current.currentTime = 0;
        currentVideoRef.current.play().catch(() => {
          // silent autoplay error
        });
      }

      // 清除現有的播放計時器
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }

      // 設定 3 秒後移除遮罩
      handWavingTimerRef.current = setTimeout(() => {
        console.log("🫷 Hand waving timer completed");
        setShowHandWavingOverlay(false);
        // 通知父組件將 isHandWaving 設回 false
        if (onHandWavingChange) {
          onHandWavingChange(false);
        }
      }, handWavingDuration);
    }

    return () => {
      if (handWavingTimerRef.current) {
        clearTimeout(handWavingTimerRef.current);
        handWavingTimerRef.current = null;
      }
    };
  }, [isHandWaving]);

  // 監聽 showHandWavingOverlay 變化，遮罩消失後重新啟動播放計時
  useEffect(() => {
    if (!showHandWavingOverlay && !isHandWaving) {
      console.log("🫷 Hand waving ended, restarting playback cycle");
      startPlaybackCycle();
    }
  }, [showHandWavingOverlay, isHandWaving]);

  // 啟動每 3 秒的播放切換邏輯（只有在沒有遮罩時才啟動）
  useEffect(() => {
    if (!showHandWavingOverlay && !isHandWaving) {
      startPlaybackCycle();
    }
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [currentIndex]);

  const startPlaybackCycle = () => {
    // 如果正在顯示遮罩，不啟動計時器
    if (showHandWavingOverlay) return;

    timerRef.current = setTimeout(() => {
      const nextIndex = getNextIndex();

      if (nextIndex !== currentIndex) {
        startTransition(nextIndex);
      } else {
        // 沒有要切換的話，重新啟動播放計時
        startPlaybackCycle();
      }
    }, interval);
  };

  const getNextIndex = () => {
    const candidate = nextIndexFromPropRef.current;

    const isValid =
      typeof candidate === "number" &&
      candidate >= 0 &&
      candidate < videos.length;

    if (isValid && candidate !== currentIndex) {
      return candidate;
    }

    // fallback 條件
    if (currentIndex === 0) return 0; // 繼續播 video[0]
    return 0; // fallback to video[0]
  };

  const startTransition = (targetIndex) => {
    if (
      isTransitioning ||
      targetIndex === currentIndex ||
      showHandWavingOverlay
    )
      return;

    const nextSrc = videos[targetIndex];
    const nextVideoRef = isSecondActive ? videoARef : videoBRef;

    if (isSecondActive) {
      setVideoA(nextSrc);
      console.log("切換到 Video A:", nextSrc, targetIndex + 1);
    } else {
      setVideoB(nextSrc);
      console.log("切換到 Video B:", nextSrc, targetIndex + 1);
    }

    setIsTransitioning(true);

    setTimeout(() => {
      if (nextVideoRef.current) {
        nextVideoRef.current.play().catch(() => {
          // silent autoplay error
        });
      }
    }, 100);

    setTimeout(() => {
      setCurrentIndex(targetIndex);
      setIsSecondActive(!isSecondActive);
      setIsTransitioning(false);
    }, transitionDuration);
  };

  const currentVideoSrc = isSecondActive ? videoB : videoA;
  const nextVideoSrc = isSecondActive ? videoA : videoB;

  if (videos.length === 0) {
    return (
      <div className="fixed inset-0 z-0 bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading videos...</div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-0 bg-black">
      {/* Video A */}
      <video
        ref={videoARef}
        className="w-full h-full object-cover absolute inset-0"
        autoPlay
        muted
        playsInline
        controls={false}
        loop
        src={videoA}
        style={{
          opacity: isSecondActive
            ? isTransitioning
              ? 1
              : 0
            : isTransitioning
            ? 0
            : 1,
          transition: `opacity ${transitionDuration}ms ease-in-out`,
          zIndex: isSecondActive ? 2 : 1,
        }}
      />

      {/* Video B */}
      <video
        ref={videoBRef}
        className="w-full h-full object-cover absolute inset-0"
        muted
        playsInline
        controls={false}
        loop
        src={videoB}
        style={{
          opacity: isSecondActive
            ? isTransitioning
              ? 0
              : 1
            : isTransitioning
            ? 1
            : 0,
          transition: `opacity ${transitionDuration}ms ease-in-out`,
          zIndex: isSecondActive ? 1 : 2,
        }}
      />

      {/* Hand Waving Overlay 遮罩 */}
      {showHandWavingOverlay && (
        <div
          className="absolute inset-0 z-20 pointer-events-none"
          style={{
            backgroundColor: "rgba(255, 255, 255, 0.1)",
            backdropFilter: "blur(3px)",
            mixBlendMode: "lighten",
            filter: "grayscale(0.3) brightness(1)",
          }}
        />
      )}

      <div className="absolute bottom-4 right-4 text-white text-sm bg-black/60 px-2 py-1 rounded z-10">
        Now playing: Video {currentIndex + 1} / {videos.length}
        {showHandWavingOverlay && (
          <div className="mt-1 text-xs text-yellow-300">Hand Waving Mode</div>
        )}
      </div>
    </div>
  );
}

export default VideoPlayer;
