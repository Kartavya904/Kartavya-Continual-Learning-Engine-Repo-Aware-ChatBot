"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

const signupSchema = z
  .object({
    first_name: z.string().min(1),
    last_name: z.string().min(1),
    email: z.string().email(),
    password: z.string().min(8),
    confirm_password: z.string().min(8),
    phone: z.string().optional(),
    address: z.string().optional(),
  })
  .refine((d) => d.password === d.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords must match",
  });

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

type Mode = "login" | "signup";

type SignupFormData = z.infer<typeof signupSchema>;
type LoginFormData = z.infer<typeof loginSchema>;
type FormData = SignupFormData | LoginFormData;

export default function AuthModal({
  mode,
  onClose,
  onSuccess,
}: {
  mode: Mode;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const form = useForm<FormData>({
    resolver: zodResolver(mode === "signup" ? signupSchema : loginSchema),
  });

  async function submit(values: FormData) {
    setError(null);
    const path = mode === "signup" ? "/api/auth/signup" : "/api/auth/login";
    const res = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(values),
    });
    const text = await res.text();
    let data: { detail?: string; error?: string; raw?: string };
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
    if (!res.ok) {
      setError(
        typeof data?.detail === "string"
          ? data.detail
          : data?.error ?? "Request failed"
      );
      return;
    }
    onSuccess();
  }

  const f = form.register;
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">
            {mode === "signup" ? "Create your account" : "Welcome back"}
          </h2>
          <button className="text-gray-500" onClick={onClose}>
            ✕
          </button>
        </div>

        <form className="space-y-3" onSubmit={form.handleSubmit(submit)}>
          {mode === "signup" && (
            <div className="grid grid-cols-2 gap-3">
              <input
                placeholder="First name *"
                className="border rounded px-3 py-2"
                {...f("first_name")}
              />
              <input
                placeholder="Last name *"
                className="border rounded px-3 py-2"
                {...f("last_name")}
              />
              <input
                placeholder="Phone"
                className="border rounded px-3 py-2 col-span-2"
                {...f("phone")}
              />
              <input
                placeholder="Address"
                className="border rounded px-3 py-2 col-span-2"
                {...f("address")}
              />
            </div>
          )}
          <input
            placeholder="Email *"
            className="border rounded px-3 py-2 w-full"
            {...f("email")}
          />
          <input
            placeholder="Password *"
            type="password"
            className="border rounded px-3 py-2 w-full"
            {...f("password")}
          />
          {mode === "signup" && (
            <input
              placeholder="Confirm password *"
              type="password"
              className="border rounded px-3 py-2 w-full"
              {...f("confirm_password")}
            />
          )}

          {error && <p className="text-red-600 text-sm">{error}</p>}

          <button
            disabled={form.formState.isSubmitting}
            className="w-full rounded bg-black text-white py-2"
          >
            {form.formState.isSubmitting
              ? "Please wait…"
              : mode === "signup"
              ? "Create account"
              : "Log in"}
          </button>
        </form>
      </div>
    </div>
  );
}
