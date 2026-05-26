import {
  IContentBlockDeltaResponse,
  IContentBlockStartResponse,
  IContentBlockStopResponse,
  IMessageDeltaResponse,
  IMessageStartResponse,
  IMessageStopResponse,
} from '@shared/ui/interfaces/stream.interfaces';

export type StreamEventType =
  | 'message_start'
  | 'content_block_start'
  | 'content_block_delta'
  | 'content_block_stop'
  | 'message_delta'
  | 'message_stop';

export type StreamMessageDeltaType =
  | 'reasoning_delta'
  | 'reasoning'
  | 'text'
  | 'text_delta';

export type StreamResponseType =
  | IMessageStartResponse
  | IContentBlockStartResponse
  | IContentBlockDeltaResponse
  | IContentBlockStopResponse
  | IMessageDeltaResponse
  | IMessageStopResponse;
