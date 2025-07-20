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

  const interval = 5000; // video playing time when there's no new index prop
  const transitionDuration = 1500; // video transition duration
  const handWavingDuration = 5000; // 10 秒遮罩持續時間
  const overlayTransitionDuration = 500; // 遮罩淡入淡出時間

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isSecondActive, setIsSecondActive] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [showHandWavingOverlay, setShowHandWavingOverlay] = useState(false);
  const [isHandWavingTransitioning, setIsHandWavingTransitioning] =
    useState(false);

  const [nextScheduledIndex, setNextScheduledIndex] = useState(0);

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
      setNextScheduledIndex(index);
    }
    console.log(`Next scheduled index: ${nextScheduledIndex}, index: ${index}`);
  }, [index]);

  useEffect(() => {
  if (typeof index === "number" && index >= 0 && index < videos.length) {
    console.log(`🔄 New index prop received: ${index}, current: ${currentIndex}`);
    
    // 如果新的 index 與當前不同，立即觸發轉場
    if (index !== currentIndex && !showHandWavingOverlay) {
      console.log(`🚀 Immediately transitioning to index: ${index}`);
      
      // 清除現有的計時器
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      
      // 更新 ref 和 scheduled index
      nextIndexFromPropRef.current = index;
      setNextScheduledIndex(index);
      
      // 立即開始轉場
      startTransition(index);
    } else {
      // 如果相同或者在手勢遮罩中，只更新 ref
      nextIndexFromPropRef.current = index;
      setNextScheduledIndex(index);
    }
  }
  
  console.log(`Next scheduled index: ${nextScheduledIndex}, index: ${index}`);
}, [index, currentIndex, showHandWavingOverlay]);

  useEffect(() => {
    if (!isTransitioning) {
      const shouldResetToZero = !(
        currentIndex === 0 &&
        (nextIndexFromPropRef.current === 0 ||
          nextIndexFromPropRef.current === null)
      );
      if (shouldResetToZero) {
        setNextScheduledIndex(0);
      }
    }
  }, [isTransitioning, currentIndex]);

  // 處理 isHandWaving 變化
  useEffect(() => {
    if (isHandWaving && !showHandWavingOverlay) {
      console.log("🫷 Hand waving started");
      // 開始手勢遮罩
      setShowHandWavingOverlay(true);

      // mask fading in starts
      setIsHandWavingTransitioning(true);

      // mask fading in ends
      setTimeout(() => {
        setIsHandWavingTransitioning(false);
      }, overlayTransitionDuration);

      // 清除現有的播放計時器
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }

      // 移除遮罩
      handWavingTimerRef.current = setTimeout(() => {
        console.log("🫷 Hand waving timer completed");
        setIsHandWavingTransitioning(true);

        setTimeout(() => {
          setShowHandWavingOverlay(false);
          setIsHandWavingTransitioning(false);
          // 通知父組件將 isHandWaving 設回 false
          if (onHandWavingChange) {
            onHandWavingChange(false);
          }
        }, overlayTransitionDuration);
      }, handWavingDuration - overlayTransitionDuration); // 提早 overlayTransitionDuration 毫秒開始移除遮罩
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
      console.log("🫷 Hand waving ended, transitioning to 0, neutral video");

      if (currentIndex !== 0) {
        startTransition(0); // 確保在遮罩結束後切換到 neutral video
      } else {
        startPlaybackCycle();
      }
    }
  }, [showHandWavingOverlay, isHandWaving]);

  // 啟動每 10 秒的播放切換邏輯（只有在沒有遮罩時才啟動）
  useEffect(() => {
    if (!showHandWavingOverlay && !isHandWaving && !isTransitioning) {
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
      console.log(`nextIndex in transition, ${nextIndex}`);

      startTransition(nextIndex)

      // if (nextIndex !== currentIndex) {
      //   startTransition(nextIndex);
      // } else {
      //   // 沒有要切換的話，重新啟動播放計時
      //   startPlaybackCycle();
      // }
    }, interval);
  };
  const getNextIndex = () => {
    console.log(`currentIndex: ${currentIndex}`);
    console.log(`propIndex: ${nextIndexFromPropRef.current}`);
    console.log(`nextScheduledIndex: ${nextScheduledIndex}`);

    // 優先取得新的 index prop
    const propIndex = nextIndexFromPropRef.current;
    const isValidPropIndex =
      typeof propIndex === "number" &&
      propIndex >= 0 &&
      propIndex < videos.length;

    if (isValidPropIndex) {
      console.log(`有新的 index, 使用它: ${propIndex}`);
      return propIndex;
    }

    // 如果當前已經是 video[0]，且沒有新的 index prop，則不切換
    // if (currentIndex === 0 && (propIndex === 0 || propIndex === null)) {
    //   console.log("已經在 video[0]");
    //   return currentIndex;
    // }

    console.log(`沒有收到新值，再次回到 0`);
    return 0;
  };

  const startTransition = (targetIndex) => {
    if (isTransitioning || showHandWavingOverlay) {
      console.log(`轉場中或是手勢遮罩中`)
      return;
    }

    const nextSrc = videos[targetIndex];
    const nextVideoRef = isSecondActive ? videoARef : videoBRef;

    if (isSecondActive) {
      setVideoA(nextSrc);
      console.log("切換到 Video A:", nextSrc, targetIndex);
    } else {
      setVideoB(nextSrc);
      console.log("切換到 Video B:", nextSrc, targetIndex);
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

      if (nextIndexFromPropRef.current === targetIndex) {
        nextIndexFromPropRef.current = null; // 清除已使用的 prop index

        if (targetIndex !== 0) {
          setNextScheduledIndex(0);
        }
      }
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
            opacity: isHandWavingTransitioning ? 0 : 1,
            transition: `opacity ${overlayTransitionDuration}ms ease-in-out`,
          }}
        />
      )}

      <div className="absolute bottom-4 right-4 text-white text-sm bg-black/60 px-2 py-1 rounded z-10">
        Now playing: Video {currentIndex} / {videos.length}
        {showHandWavingOverlay && (
          <div className="mt-1 text-xs text-yellow-300">Hand Waving Mode</div>
        )}
      </div>
    </div>
  );
}

export default VideoPlayer;
