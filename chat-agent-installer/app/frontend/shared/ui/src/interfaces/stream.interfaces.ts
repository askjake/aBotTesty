import {
  StreamEventType,
  StreamMessageDeltaType,
} from '@shared/ui/types/stream.types';
import { Readable } from 'node:stream';

interface IBaseStreamResponse {
  event: StreamEventType;
}

export interface IMessageStartResponse extends IBaseStreamResponse {
  event: 'message_start';
  data: {
    type: 'message_start';
    message: {
      input_message_id: string;
      response_message_id: string;
      type: 'message';
      role: 'assistant';
      content: any[];
      model: string;
      stop_reason: null | string;
      title: null | string;
    };
  };
}

export interface IContentBlockStartResponse extends IBaseStreamResponse {
  event: 'content_block_start';
  data: {
    type: 'content_block_start';
    index: number;
    content_block: {
      type: StreamMessageDeltaType;
      text?: string;
      reasoning?: string;
    };
  };
}

export interface IContentBlockDeltaResponse extends IBaseStreamResponse {
  event: 'content_block_delta';
  data: {
    type: 'content_block_delta';
    index: number;
    delta: {
      type: StreamMessageDeltaType;
      text?: string;
      reasoning?: string;
    };
  };
}

export interface IContentBlockStopResponse extends IBaseStreamResponse {
  event: 'content_block_stop';
  data: {
    type: 'content_block_stop';
    index: number;
  };
}

export interface IMessageDeltaResponse extends IBaseStreamResponse {
  event: 'message_delta';
  data: {
    type: 'message_delta';
    delta: {
      stop_reason: string;
      title: string;
      error_msg: string;
    };
  };
}

export interface IMessageStopResponse extends IBaseStreamResponse {
  event: 'message_stop';
  data: {
    type: 'message_stop';
  };
}

export interface IFileStream extends Readable {
  fieldname: string;
  originalname: string;
  encoding: string;
  mimetype: string;
  size: number;
  destination?: string;
  filename?: string;
  path?: string;
  buffer?: Buffer;
}
