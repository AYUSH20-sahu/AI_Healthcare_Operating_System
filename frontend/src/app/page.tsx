export default function HomePage() {
    return (
        <main className="min-h-screen flex flex-col items-center justify-center p-8">
            <div className="max-w-2xl text-center">
                <h1 className="text-4xl font-bold text-primary-600 mb-4">AI-HOS</h1>
                <p className="text-xl text-gray-600 mb-8">
                    AI Healthcare Operating System
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <a
                        href="/patient"
                        className="p-6 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-200"
                    >
                        <h2 className="text-xl font-semibold text-primary-600 mb-2">Patient Portal</h2>
                        <p className="text-gray-600">Voice intake, appointments, health records</p>
                    </a>
                    <a
                        href="/doctor"
                        className="p-6 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-200"
                    >
                        <h2 className="text-xl font-semibold text-primary-600 mb-2">Doctor Dashboard</h2>
                        <p className="text-gray-600">AI Copilot, scribe, prescriptions</p>
                    </a>
                    <a
                        href="/admin"
                        className="p-6 bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow border border-gray-200"
                    >
                        <h2 className="text-xl font-semibold text-primary-600 mb-2">Admin Console</h2>
                        <p className="text-gray-600">Operations, analytics, management</p>
                    </a>
                </div>
            </div>
        </main>
    )
}