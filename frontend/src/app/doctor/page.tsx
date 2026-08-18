export default function DoctorPage() {
    return (
        <main className="min-h-screen flex flex-col items-center justify-center p-8">
            <div className="max-w-2xl text-center">
                <h1 className="text-4xl font-bold text-primary-600 mb-4">Doctor Dashboard</h1>
                <p className="text-xl text-gray-600 mb-8">
                    AI Copilot, ambient scribe, prescription drafting
                </p>
                <div className="space-y-4">
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">AI Copilot</h2>
                        <p className="text-gray-600">Real-time clinical decision support and recommendations</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">Ambient Scribe</h2>
                        <p className="text-gray-600">Automatic clinical note generation from consultations</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">Prescription Drafting</h2>
                        <p className="text-gray-600">AI-assisted prescription creation with interaction checks</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">Patient Management</h2>
                        <p className="text-gray-600">View patient history, records, and upcoming appointments</p>
                    </div>
                </div>
                <a
                    href="/"
                    className="mt-8 inline-block text-primary-600 hover:text-primary-700 font-medium"
                >
                    ← Back to Home
                </a>
            </div>
        </main>
    )
}