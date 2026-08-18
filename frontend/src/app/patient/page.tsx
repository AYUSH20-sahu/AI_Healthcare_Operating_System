export default function PatientPage() {
    return (
        <main className="min-h-screen flex flex-col items-center justify-center p-8">
            <div className="max-w-2xl text-center">
                <h1 className="text-4xl font-bold text-primary-600 mb-4">Patient Portal</h1>
                <p className="text-xl text-gray-600 mb-8">
                    Voice intake, appointment booking, health records access
                </p>
                <div className="space-y-4">
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">AI Receptionist (Voice Intake)</h2>
                        <p className="text-gray-600">Natural language symptom collection and triage routing</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">Appointment Booking</h2>
                        <p className="text-gray-600">Schedule, reschedule, and manage appointments</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">Health Records</h2>
                        <p className="text-gray-600">Access medical records, prescriptions, and visit summaries</p>
                    </div>
                    <div className="p-6 bg-white rounded-xl shadow-md border border-gray-200 text-left">
                        <h2 className="text-lg font-semibold text-gray-800 mb-2">Multilingual Support</h2>
                        <p className="text-gray-600">Voice and text support in multiple languages</p>
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