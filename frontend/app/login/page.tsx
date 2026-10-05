import { LoginForm } from "@/components/auth/LoginForm";
import { safeRedirectPath } from "@/lib/auth/redirects";

type LoginPageProps = {
  searchParams: Promise<{ next?: string | string[] }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const requestedNext = Array.isArray(params.next) ? params.next[0] : params.next;

  return (
    <main className="mx-auto flex min-h-[70vh] max-w-md items-center px-4">
      <section className="panel w-full p-8">
        <p className="eyebrow">Comunio Data</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Anmelden</h1>
        <p className="mt-3 text-sm leading-6 text-secondary">
          Melde dich an, um auf das Comunio-Dashboard zuzugreifen.
        </p>
        <LoginForm nextPath={safeRedirectPath(requestedNext)} />
      </section>
    </main>
  );
}
