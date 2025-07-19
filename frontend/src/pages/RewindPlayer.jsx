function RewindPlayer() {

  const rewindVideo = "videos/sad.mp4";

  return (
    <>
      <video className="w-full h-full object-cover absolute inset-0" muted autoPlay playsInline controls={false} loop src={rewindVideo} />
    </>
  );
}

export default RewindPlayer;