"use client";

export default function TemizleButton() {
  return (
    <form
      method="post"
      action="/api/hatalar/temizle"
      onSubmit={(e) => {
        if (!window.confirm("Tüm hata kayıtları silinecek. Emin misin?")) {
          e.preventDefault();
        }
      }}
    >
      <button
        type="submit"
        className="text-xs rounded border border-zinc-700 text-zinc-400 px-2.5 py-1 hover:bg-zinc-800 hover:text-zinc-200"
      >
        Tümünü temizle
      </button>
    </form>
  );
}
