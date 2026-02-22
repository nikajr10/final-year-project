import React from 'react';
import { Stack } from 'expo-router';

export default function AuthLayout() {
    return (
        <Stack
            screenOptions={{
                headerShown: false,
                // animationEnabled: true,
            }}
        >
            <Stack.Screen
                name="login"
                options={{
                    title: 'Login',
                }}
            />
            <Stack.Screen
                name="signup"
                options={{
                    title: 'Sign Up',
                }}
            />
            <Stack.Screen
                name="forgot-password"
                options={{
                    title: 'Forgot Password',
                }}
            />
        </Stack>
    );
}