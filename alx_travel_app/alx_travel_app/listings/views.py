from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
import uuid
from django.conf import settings
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Payment


class Index(APIView):
    def get(self,request):
        return Response({"hello there"})


class InitiatePaymentView(APIView):
    """
    Initiate a payment via Chapa
    """

    def post(self, request):
        try:
            data = request.data
            amount = data.get("amount")
            email = data.get("email")
            first_name = data.get("first_name")
            last_name = data.get("last_name")
            booking_reference = str(uuid.uuid4())

            # Save a pending payment
            payment = Payment.objects.create(
                booking_reference=booking_reference,
                amount=amount,
                status="Pending"
            )

            # Prepare Chapa API request
            chapa_url = f"{settings.CHAPA_BASE_URL}/transaction/initialize"
            headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
            payload = {
                "amount": amount,
                "currency": "ETB",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "tx_ref": booking_reference,
                "callback_url": "http://localhost:8000/api/payments/verify/",
                "return_url": "http://localhost:8000/payment-success/",
                "customization": {
                    "title": "Travel Booking Payment",
                    "description": "Payment for travel booking via Chapa"
                }
            }

            response = requests.post(chapa_url, json=payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("status") == "success":
                checkout_url = response_data["data"]["checkout_url"]
                payment.transaction_id = response_data["data"]["tx_ref"]
                payment.save()

                return Response({
                    "message": "Payment initiated successfully.",
                    "checkout_url": checkout_url,
                    "booking_reference": booking_reference
                }, status=status.HTTP_200_OK)
            else:
                payment.status = "Failed"
                payment.save()
                return Response({
                    "error": "Payment initiation failed.",
                    "details": response_data
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPaymentView(APIView):
    """
    Verify payment status after user completes the payment
    """

    def get(self, request):
        tx_ref = request.GET.get("tx_ref")
        if not tx_ref:
            return Response({"error": "Transaction reference is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(booking_reference=tx_ref)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        verify_url = f"{settings.CHAPA_BASE_URL}/transaction/verify/{tx_ref}"
        headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}

        response = requests.get(verify_url, headers=headers)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("status") == "success":
            chapa_status = response_data["data"]["status"]
            if chapa_status == "success":
                payment.status = "Completed"
                payment.save()
                return Response({
                    "message": "Payment verified successfully.",
                    "status": payment.status,
                    "booking_reference": payment.booking_reference,
                    "amount": payment.amount
                }, status=status.HTTP_200_OK)
            else:
                payment.status = "Failed"
                payment.save()
                return Response({
                    "message": "Payment failed or not completed.",
                    "status": payment.status
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                "error": "Verification failed.",
                "details": response_data
            }, status=status.HTTP_400_BAD_REQUEST)
